"""
EVALUATION SUITE - Level 4 Final
Teste fact lookup, aggregations, et citation faithfulness
"""

import pytest
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

from src.agent.sql_generator import SQLGenerator
from src.agent.query_executor import QueryExecutor
from src.agent.response_generator import ResponseGenerator
from src.utils.config import DB_PATH


class TestEvaluationSuite:
    """Suite d'évaluation complète pour validation automatique"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup composants"""
        self.sql_gen = SQLGenerator()
        self.executor = QueryExecutor(DB_PATH)
        self.executor.connect()
        self.response_gen = ResponseGenerator()
        
        # Résultats
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
    
    def teardown_method(self):
        """Sauvegarder résultats"""
        output_dir = Path("tests/evaluation_results")
        output_dir.mkdir(exist_ok=True)
        
        # Calculer summary
        total = len(self.results["tests"])
        passed = sum(1 for t in self.results["tests"] if t["passed"])
        
        self.results["summary"] = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "accuracy": round(passed / total * 100, 2) if total > 0 else 0
        }
        
        # Sauvegarder
        with open(output_dir / "metrics_summary.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 Résultats sauvegardés : tests/evaluation_results/metrics_summary.json")
        print(f"✅ Passed: {passed}/{total} ({self.results['summary']['accuracy']}%)")
    
    def _run_test_case(self, question: str, expected_answer, tolerance=None, test_type="fact_lookup"):
        """Exécute un cas de test"""
        
        # Générer SQL
        sql_result = self.sql_gen.generate_sql(question)
        
        if not sql_result['success']:
            return {
                "question": question,
                "test_type": test_type,
                "passed": False,
                "error": "SQL generation failed",
                "expected": expected_answer,
                "actual": None
            }
        
        # Exécuter
        result = self.executor.execute(sql_result['sql'])
        
        if not result['success']:
            return {
                "question": question,
                "test_type": test_type,
                "passed": False,
                "error": "SQL execution failed",
                "expected": expected_answer,
                "actual": None,
                "sql": sql_result['sql']
            }
        
        data = result['data']
        
        # Vérifier résultat
        if data.empty:
            actual = None
        elif len(data) == 1 and len(data.columns) == 1:
            actual = data.iloc[0, 0]
        else:
            actual = len(data)  # Nombre de résultats
        
        # Comparer
        if tolerance:
            passed = abs(actual - expected_answer) <= tolerance
        else:
            passed = actual == expected_answer
        
        return {
            "question": question,
            "test_type": test_type,
            "passed": passed,
            "expected": expected_answer,
            "actual": actual,
            "sql": sql_result['sql'],
            "error": None if passed else f"Expected {expected_answer}, got {actual}"
        }
    
    # ========================================================================
    # TEST 1 : FACT LOOKUP ACCURACY
    # ========================================================================
    
    def test_fact_lookup_accuracy(self):
        """Teste la précision des réponses factuelles"""
        
        test_cases = [
            # (question, expected_answer, tolerance)
            ("Combien de sièges a gagné le RHDP ?", 135, 0),
            ("Combien de sièges a gagné le PDCI-RDA ?", 50, 0),
            ("Combien de circonscriptions au total ?", 206, 0),
            ("Qui a gagné à Cocody ?", "PDCI-RDA", None),
            ("Qui a gagné à Yopougon ?", "RHDP", None),
            ("Combien de candidats indépendants élus ?", 16, 1),  # tolerance ±1
        ]
        
        print("\n📊 Test 1/3 : Fact Lookup Accuracy")
        
        for question, expected, tolerance in test_cases:
            result = self._run_test_case(question, expected, tolerance, "fact_lookup")
            self.results["tests"].append(result)
            
            status = "✅" if result["passed"] else "❌"
            print(f"  {status} {question}")
            if not result["passed"]:
                print(f"      Expected: {expected}, Got: {result['actual']}")
    
    # ========================================================================
    # TEST 2 : AGGREGATION CORRECTNESS
    # ========================================================================
    
    def test_aggregation_correctness(self):
        """Teste la justesse des agrégations"""
        
        test_cases = [
            # Rankings
            ("Top 3 des régions par nombre de sièges RHDP", 3, None),
            ("Top 10 des candidats par score", 10, None),
            
            # Counts
            ("Combien de partis différents ont gagné au moins 1 siège ?", 5, 1),
            
            # Averages (avec tolérance)
            ("Taux de participation moyen national", 20.0, 5.0),  # ±5%
        ]
        
        print("\n📊 Test 2/3 : Aggregation Correctness")
        
        for question, expected, tolerance in test_cases:
            result = self._run_test_case(question, expected, tolerance, "aggregation")
            self.results["tests"].append(result)
            
            status = "✅" if result["passed"] else "❌"
            print(f"  {status} {question}")
            if not result["passed"]:
                print(f"      Expected: {expected}, Got: {result['actual']}")
    
    # ========================================================================
    # TEST 3 : CITATION FAITHFULNESS
    # ========================================================================
    
    def test_citation_faithfulness(self):
        """Vérifie que les citations correspondent aux sources réelles"""
        
        test_cases = [
            {
                "question": "Qui a gagné à Cocody ?",
                "expected_pages": [41],  # Page où se trouve Cocody
                "expected_entity": "PDCI-RDA"
            },
            {
                "question": "Résultats de Yopougon",
                "expected_pages": [47],
                "expected_entity": "RHDP"
            },
            {
                "question": "Résultats de Koumassi",
                "expected_pages": [42],
                "expected_entity": "RHDP"
            }
        ]
        
        print("\n📊 Test 3/3 : Citation Faithfulness")
        
        for case in test_cases:
            # Générer réponse avec citations
            sql_result = self.sql_gen.generate_sql(case["question"])
            
            if not sql_result['success']:
                result = {
                    "question": case["question"],
                    "test_type": "citation_faithfulness",
                    "passed": False,
                    "error": "SQL generation failed",
                    "expected_pages": case["expected_pages"]
                }
                self.results["tests"].append(result)
                continue
            
            exec_result = self.executor.execute(sql_result['sql'])
            
            if not exec_result['success'] or exec_result['data'].empty:
                result = {
                    "question": case["question"],
                    "test_type": "citation_faithfulness",
                    "passed": False,
                    "error": "No data returned",
                    "expected_pages": case["expected_pages"]
                }
                self.results["tests"].append(result)
                continue
            
            data = exec_result['data']
            
            # Vérifier présence de source_page
            if 'source_page' not in data.columns:
                result = {
                    "question": case["question"],
                    "test_type": "citation_faithfulness",
                    "passed": False,
                    "error": "No source_page in results",
                    "expected_pages": case["expected_pages"]
                }
                self.results["tests"].append(result)
                print(f"  ❌ {case['question']}")
                print(f"      Error: No source_page column")
                continue
            
            # Extraire pages citées
            cited_pages = data['source_page'].dropna().unique().tolist()
            cited_pages = [int(p) for p in cited_pages]
            
            # Vérifier concordance
            passed = all(p in cited_pages for p in case["expected_pages"])
            
            result = {
                "question": case["question"],
                "test_type": "citation_faithfulness",
                "passed": passed,
                "expected_pages": case["expected_pages"],
                "actual_pages": cited_pages,
                "error": None if passed else f"Pages mismatch: expected {case['expected_pages']}, got {cited_pages}"
            }
            
            self.results["tests"].append(result)
            
            status = "✅" if passed else "❌"
            print(f"  {status} {case['question']}")
            if not passed:
                print(f"      Expected pages: {case['expected_pages']}, Got: {cited_pages}")


# ========================================================================
# FONCTION UTILITAIRE : Générer rapport détaillé
# ========================================================================

def generate_detailed_report():
    """Génère un rapport détaillé avec tous les échecs"""
    
    results_path = Path("tests/evaluation_results/metrics_summary.json")
    
    if not results_path.exists():
        print("❌ Aucun résultat trouvé. Lancez d'abord : pytest tests/test_evaluation_suite.py")
        return
    
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    print("\n" + "="*70)
    print("📊 RAPPORT D'ÉVALUATION DÉTAILLÉ")
    print("="*70)
    
    print(f"\n🕒 Timestamp : {results['timestamp']}")
    print(f"\n📈 Summary :")
    print(f"  Total tests : {results['summary']['total_tests']}")
    print(f"  ✅ Passed   : {results['summary']['passed']}")
    print(f"  ❌ Failed   : {results['summary']['failed']}")
    print(f"  🎯 Accuracy : {results['summary']['accuracy']}%")
    
    # Échecs détaillés
    failures = [t for t in results['tests'] if not t['passed']]
    
    if failures:
        print(f"\n❌ ÉCHECS DÉTAILLÉS ({len(failures)}) :")
        for i, fail in enumerate(failures, 1):
            print(f"\n  {i}. {fail['question']}")
            print(f"     Type: {fail['test_type']}")
            print(f"     Error: {fail['error']}")
            if 'sql' in fail and fail['sql']:
                print(f"     SQL: {fail['sql'][:100]}...")
    else:
        print("\n✅ AUCUN ÉCHEC - Tous les tests passent !")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    # Lancer tests + générer rapport
    import subprocess
    
    print("🚀 Lancement de l'évaluation complète...\n")
    
    subprocess.run([
        "pytest", 
        "tests/test_evaluation_suite.py", 
        "-v",
        "--tb=short"
    ])
    
    print("\n📊 Génération du rapport détaillé...\n")
    generate_detailed_report()