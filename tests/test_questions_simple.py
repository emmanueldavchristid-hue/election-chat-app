"""
🧪 TEST AUTOMATIQUE AMÉLIORÉ - Election Chat App
Version avec affichage détaillé des réponses et validation de cohérence

USAGE:
    python scripts/test_questions_improved.py
"""

import sys
from pathlib import Path
import time
import json
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.sql_generator import SQLGenerator
from src.agent.query_validator import QueryValidator
from src.agent.query_executor import QueryExecutor
from src.agent.response_generator import ResponseGenerator
from src.agent.intent_classifier import IntentClassifier
from src.utils.config import DB_PATH

# Test questions critiques seulement
TEST_QUESTIONS = {
    "🟢 TESTS CRITIQUES": [
        ("Combien de sièges a gagné le RHDP ?", "aggregation", "CRITIQUE", "155"),
        ("Qui a gagné à Cocody ?", "lookup", "CRITIQUE", None),
        ("Combien de voix a obtenu le PDCI-RDA ?", "aggregation", "CRITIQUE", None),
        ("Combien de bulletins nuls à Adjamé ?", "lookup", "CRITIQUE", None),
        ("Top 5 des candidats avec le plus de voix", "ranking", "CRITIQUE", None),
        ("Quels sont les 3 partis avec le plus de sièges ?", "ranking", "CRITIQUE", None),
    ],
}


class ImprovedQuestionTester:
    """Test automatique amélioré avec validation"""
    
    def __init__(self):
        print("🔧 Initialisation du testeur amélioré...")
        
        self.sql_generator = SQLGenerator()
        self.query_validator = QueryValidator(max_limit=1000)
        self.query_executor = QueryExecutor(DB_PATH)
        self.response_generator = ResponseGenerator()
        self.intent_classifier = IntentClassifier()
        
        self.query_executor.connect()
        
        print("✅ Testeur initialisé\n")
    
    def _validate_response(self, question: str, response_text: str, data: pd.DataFrame) -> List[str]:
        """Valide la cohérence de la réponse"""
        issues = []
        
        # CHECK 1: Réponse "nan"
        if response_text.strip().lower() in ["nan", "none", "null", ""]:
            issues.append("🔴 CRITIQUE: Réponse vide ou 'nan'")
            return issues
        
        # CHECK 2: Questions d'agrégation doivent contenir des nombres
        if any(word in question.lower() for word in ["combien", "nombre", "total"]):
            numbers = re.findall(r'\b\d+\b', response_text)
            
            if not numbers:
                # Pas de nombre dans la réponse
                issues.append("⚠️ Question d'agrégation sans nombre dans la réponse")
                
                # Cas spécial: nom de parti au lieu du chiffre
                if any(word in response_text.upper() for word in ["RHDP", "PDCI", "INDEPENDANT"]):
                    issues.append("🔴 CRITIQUE: Nom de parti affiché au lieu du nombre")
        
        # CHECK 3: Vérifier que la réponse n'est pas juste le SQL
        if "SELECT" in response_text.upper():
            issues.append("⚠️ SQL visible dans la réponse")
        
        return issues
    
    def test_question(self, question: str, expected_value: str = None) -> Dict[str, Any]:
        """Teste une question et affiche les résultats détaillés"""
        start_time = time.time()
        
        result = {
            "question": question,
            "success": False,
            "response_text": None,
            "sql": None,
            "rows_returned": 0,
            "duration_s": 0,
            "issues": [],
            "expected": expected_value,
            "actual": None
        }
        
        try:
            # 1. Classification intent
            intent_result = self.intent_classifier.classify(question)
            intent = intent_result.get('intent', 'unknown')
            
            if intent == "sql_query":
                # 2. Génération SQL
                sql_result = self.sql_generator.generate_sql(question)
                
                if sql_result['success']:
                    result["sql"] = sql_result['sql']
                    
                    # 3. Validation
                    validation = self.query_validator.validate(sql_result['sql'])
                    
                    if validation['valid']:
                        # 4. Exécution
                        exec_result = self.query_executor.execute(validation['sanitized_sql'])
                        
                        if exec_result['success']:
                            data = exec_result['data']
                            result["rows_returned"] = len(data)
                            
                            # 5. Génération réponse
                            response_result = self.response_generator.generate_response(
                                question=question,
                                data=data,
                                sql=sql_result['sql']
                            )
                            
                            if response_result['success']:
                                response_text = response_result['response']
                                result["response_text"] = response_text
                                result["success"] = True
                                
                                # ✅ Extraire la valeur réelle
                                if expected_value:
                                    numbers = re.findall(r'\b\d+\b', response_text)
                                    result["actual"] = numbers[0] if numbers else response_text[:50]
                                
                                # ✅ Validation
                                issues = self._validate_response(question, response_text, data)
                                result["issues"] = issues
                                
                                # Si issues critiques, marquer comme échec
                                if any("🔴" in issue for issue in issues):
                                    result["success"] = False
                            else:
                                result["issues"].append(f"❌ Response generation failed")
                        else:
                            result["issues"].append(f"❌ SQL execution: {exec_result.get('error', 'Unknown')}")
                    else:
                        result["issues"].append(f"❌ SQL invalid: {validation.get('reason')}")
                else:
                    result["issues"].append(f"❌ SQL generation failed")
            
            else:
                result["success"] = True  # Intents non-SQL sont OK
        
        except Exception as e:
            result["issues"].append(f"❌ Exception: {str(e)}")
        
        finally:
            result["duration_s"] = round(time.time() - start_time, 2)
        
        return result
    
    def run_tests(self):
        """Lance tous les tests avec affichage détaillé"""
        print("="*80)
        print("🚀 TESTS AUTOMATIQUES AVEC VALIDATION")
        print("="*80)
        print()
        
        all_results = []
        
        for category, questions in TEST_QUESTIONS.items():
            print(f"\n{category}")
            print("-"*80)
            
            for i, test_data in enumerate(questions, 1):
                question = test_data[0]
                expected = test_data[3] if len(test_data) > 3 else None
                
                print(f"\n[{i}] 🧪 {question}")
                
                result = self.test_question(question, expected)
                all_results.append(result)
                
                # Afficher résultat
                if result["success"] and not result["issues"]:
                    print(f"   ✅ SUCCÈS ({result['duration_s']}s)")
                    
                    # Afficher la réponse
                    if result["response_text"]:
                        # Nettoyer la réponse (enlever markdown/emojis)
                        clean_response = result["response_text"].replace("**", "").replace("📄", "").replace("🔍", "")
                        # Prendre seulement les 2 premières lignes
                        lines = clean_response.split('\n')[:2]
                        response_preview = '\n'.join(lines).strip()
                        
                        print(f"   💬 Réponse: {response_preview}")
                    
                    # Validation expected vs actual
                    if expected and result["actual"]:
                        if expected == result["actual"]:
                            print(f"   ✅ Validation: {expected} (correct)")
                        else:
                            print(f"   ❌ Validation: attendu={expected}, reçu={result['actual']}")
                    
                    print(f"   📊 Données: {result['rows_returned']} ligne(s)")
                
                else:
                    print(f"   ❌ ÉCHEC")
                    
                    # Afficher la réponse même en échec
                    if result["response_text"]:
                        clean_response = result["response_text"].replace("**", "").strip()
                        print(f"   💬 Réponse: {clean_response[:100]}")
                    
                    if result["issues"]:
                        for issue in result["issues"]:
                            print(f"      {issue}")
                    
                    if result["sql"]:
                        print(f"   🔍 SQL: {result['sql'][:100]}...")
                
                time.sleep(0.5)
        
        # Résumé
        print("\n" + "="*80)
        print("📊 RÉSUMÉ")
        print("="*80)
        
        total = len(all_results)
        success = sum(1 for r in all_results if r["success"])
        critical_issues = sum(1 for r in all_results if any("🔴" in i for i in r["issues"]))
        
        print(f"\n✅ Taux de succès: {round(100*success/total, 1)}% ({success}/{total})")
        print(f"🔴 Problèmes critiques: {critical_issues}")
        
        # Afficher les problèmes critiques
        if critical_issues > 0:
            print("\n🔴 PROBLÈMES CRITIQUES DÉTECTÉS:")
            for r in all_results:
                if any("🔴" in i for i in r["issues"]):
                    print(f"\n   Question: {r['question']}")
                    print(f"   Réponse: {r['response_text'][:80] if r['response_text'] else 'N/A'}")
                    for issue in r["issues"]:
                        if "🔴" in issue:
                            print(f"   {issue}")
        
        print("\n" + "="*80)
        
        return all_results


def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║     🧪 TEST AMÉLIORÉ - Validation détaillée des réponses       ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    tester = ImprovedQuestionTester()
    results = tester.run_tests()
    
    # Sauvegarder
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = output_dir / f"detailed_results_{timestamp}.json"
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats sauvegardés: {json_file}")


if __name__ == "__main__":
    main()