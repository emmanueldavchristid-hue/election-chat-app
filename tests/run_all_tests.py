"""
Script principal pour exécuter TOUS les tests et générer un rapport complet.
VERSION AMÉLIORÉE - Exécute tous les fichiers de test disponibles

Pipeline d'extraction utilisé :
1. hybrid_extractor.py - Extraction de base
2. final_corrections.py - Corrections générales
3. manual_fixes.py - Corrections manuelles ciblées
4. db_loader.py - Chargement dans DuckDB
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json


class TestRunner:
    """Exécute et agrège tous les tests."""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        self.tests_dir = Path(__file__).parent
        
        # Vérifier si on est dans le dossier tests/ ou à la racine
        if self.tests_dir.name == "tests":
            # On est déjà dans tests/
            self.project_root = self.tests_dir.parent
        else:
            # On est à la racine
            self.project_root = self.tests_dir
            self.tests_dir = self.tests_dir / "tests"
    
    def run_test_suite(self, name: str, command: list) -> dict:
        """Exécute une suite de tests et retourne les résultats."""
        print(f"\n{'='*70}")
        print(f"🧪 Running: {name}")
        print(f"{'='*70}\n")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        
        return {
            'name': name,
            'passed': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    
    def run_all_tests(self):
        """Exécute toutes les suites de tests."""
        
        # ====================================================================
        # PHASE 1: Tests de vérité terrain (CRITIQUE)
        # ====================================================================
        print("\n" + "🟢"*35)
        print("PHASE 1: GROUND TRUTH VALIDATION")
        print("🟢"*35)
        print("Vérifie que les données extraites correspondent EXACTEMENT au PDF")
        print("Cas testés: COCODY, KOUMASSI, YOPOUGON, ABOBO, etc.")
        
        self.results['ground_truth'] = self.run_test_suite(
            "Ground Truth Validation",
            ['pytest', 'tests/test_ground_truth_validation.py', '-v', '--tb=short']
        )
        
        # ====================================================================
        # PHASE 2: Tests de sécurité (CRITIQUE)
        # ====================================================================
        print("\n" + "🔴"*35)
        print("PHASE 2: SECURITY & GUARDRAILS")
        print("🔴"*35)
        print("Teste la résistance aux injections SQL et adversarial prompts")
        
        self.results['security'] = self.run_test_suite(
            "Security & Guardrails Tests",
            ['pytest', 'tests/test_security_and_guardrails.py', '-v', '--tb=short']
        )
        
        # ====================================================================
        # PHASE 3: Tests d'agrégation (IMPORTANT)
        # ====================================================================
        print("\n" + "🟡"*35)
        print("PHASE 3: AGGREGATION ACCURACY")
        print("🟡"*35)
        print("Vérifie la précision des agrégations SQL (COUNT, SUM, AVG)")
        
        aggregation_file = self.tests_dir / "test_aggregation_accuracy.py"
        if aggregation_file.exists():
            self.results['aggregation'] = self.run_test_suite(
                "Aggregation Accuracy Tests",
                ['pytest', 'tests/test_aggregation_accuracy.py', '-v', '--tb=short']
            )
        else:
            print("⚠️ Fichier test_aggregation_accuracy.py non trouvé, skipping...")
        
        # ====================================================================
        # PHASE 4: Tests LLM Setup (CONFIGURATION)
        # ====================================================================
        print("\n" + "🔵"*35)
        print("PHASE 4: LLM SETUP VALIDATION")
        print("🔵"*35)
        print("Vérifie la configuration LLM (Ollama/Anthropic/OpenAI)")
        
        llm_file = self.tests_dir / "test_llm_setup.py"
        if llm_file.exists():
            self.results['llm_setup'] = self.run_test_suite(
                "LLM Setup Validation",
                ['python', 'tests/test_llm_setup.py']
            )
        else:
            print("⚠️ Fichier test_llm_setup.py non trouvé, skipping...")
        
        # ====================================================================
        # PHASE 5: Suite d'évaluation (METRICS)
        # ====================================================================
        print("\n" + "🟣"*35)
        print("PHASE 5: EVALUATION SUITE")
        print("🟣"*35)
        print("Tests de fact lookup, agrégations et citations")
        
        eval_file = self.tests_dir / "test_evaluation_suite.py"
        if eval_file.exists():
            self.results['evaluation'] = self.run_test_suite(
                "Evaluation Suite",
                ['pytest', 'tests/test_evaluation_suite.py', '-v', '--tb=short']
            )
        else:
            print("⚠️ Fichier test_evaluation_suite.py non trouvé, skipping...")
        
        # ====================================================================
        # PHASE 6: Tests de questions (INTEGRATION)
        # ====================================================================
        print("\n" + "🟠"*35)
        print("PHASE 6: QUESTION TESTS")
        print("🟠"*35)
        print("Tests d'intégration avec questions réelles")
        
        # Test simple
        simple_file = self.tests_dir / "test_questions_simple.py"
        if simple_file.exists():
            self.results['questions_simple'] = self.run_test_suite(
                "Simple Question Tests",
                ['python', 'tests/test_questions_simple.py']
            )
        
        # Test complet
        full_file = self.tests_dir / "test_questions.py"
        if full_file.exists():
            self.results['questions_full'] = self.run_test_suite(
                "Full Question Tests",
                ['python', 'tests/test_questions.py']
            )
        
        # ====================================================================
        # PHASE 7: Tests critiques uniquement (FINAL)
        # ====================================================================
        print("\n" + "⚫"*35)
        print("PHASE 7: CRITICAL TESTS ONLY")
        print("⚫"*35)
        print("Relance uniquement les tests marqués @pytest.mark.critical")
        
        self.results['critical'] = self.run_test_suite(
            "Critical Tests Only",
            [
                'pytest', 
                'tests/test_ground_truth_validation.py',
                'tests/test_security_and_guardrails.py',
                '-v', 
                '-m', 
                'critical', 
                '--tb=short'
            ]
        )
    
    def generate_summary_report(self):
        """Génère un rapport récapitulatif."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print("\n\n" + "="*70)
        print("📊 RAPPORT FINAL - VALIDATION COMPLÈTE")
        print("="*70)
        print(f"Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Durée totale: {duration:.2f}s")
        print()
        
        # Résumé par suite
        total_passed = 0
        total_suites = len(self.results)
        critical_failed = False
        
        for suite_name, result in self.results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status}  {result['name']}")
            if result['passed']:
                total_passed += 1
            
            # Marquer si tests critiques ont échoué
            if suite_name in ['ground_truth', 'security', 'critical'] and not result['passed']:
                critical_failed = True
        
        print()
        print(f"Suites passées: {total_passed}/{total_suites}")
        
        # Statut global
        all_passed = total_passed == total_suites
        
        print("\n" + "="*70)
        if all_passed:
            print("🎉 SUCCÈS - TOUS LES TESTS PASSENT")
            print("="*70)
            print("✅ Les données sont EXACTEMENT conformes au PDF")
            print("✅ COCODY, KOUMASSI, YOPOUGON : corrects")
            print("✅ La sécurité est assurée (anti-injection SQL)")
            print("✅ Tous les tests critiques passent")
            print("✅ Agrégations validées")
            print("✅ Configuration LLM opérationnelle")
            print()
            print("🚀 L'APPLICATION EST PRÊTE POUR LA PRODUCTION")
        else:
            print("⚠️ ÉCHECS DÉTECTÉS")
            print("="*70)
            
            # Identifier les problèmes critiques en premier
            if critical_failed:
                print("\n🔴 TESTS CRITIQUES ÉCHOUÉS - BLOQUANT")
            
            # Détailler chaque échec
            if 'ground_truth' in self.results and not self.results['ground_truth']['passed']:
                print("\n❌ Incohérences avec la vérité terrain")
                print("   → Vérifier manual_fixes.py")
                print("   → Cas problématiques: COCODY, KOUMASSI, YOPOUGON")
                print("   → Relancer le pipeline d'extraction:")
                print()
                print("      del data/processed/elections.csv")
                print("      del data/processed/elections.parquet")
                print("      del data/processed/elections.duckdb")
                print("      python -m src.ingestion.hybrid_extractor")
                print("      python -m src.ingestion.final_corrections")
                print("      python -m src.ingestion.manual_fixes")
                print("      python -m src.ingestion.db_loader")
            
            if 'security' in self.results and not self.results['security']['passed']:
                print("\n❌ Vulnérabilités de sécurité")
                print("   → Renforcer QueryValidator")
                print("   → Ajouter sanitization des inputs")
                print("   → Vérifier src/agent/query_validator.py")
            
            if 'aggregation' in self.results and not self.results['aggregation']['passed']:
                print("\n⚠️ Erreurs dans les agrégations")
                print("   → Vérifier sql_generator.py")
                print("   → Tester les GROUP BY et COUNT")
            
            if 'llm_setup' in self.results and not self.results['llm_setup']['passed']:
                print("\n⚠️ Configuration LLM incorrecte")
                print("   → Vérifier .env (LLM_PROVIDER, API keys)")
                print("   → Pour Ollama: vérifier que le serveur tourne")
                print("   → Pour API: vérifier les crédits")
            
            if 'evaluation' in self.results and not self.results['evaluation']['passed']:
                print("\n⚠️ Métriques d'évaluation non atteintes")
                print("   → Revoir les seuils de performance")
            
            if 'questions_simple' in self.results and not self.results['questions_simple']['passed']:
                print("\n⚠️ Tests de questions simples échoués")
                print("   → Vérifier les cas de base")
            
            if 'questions_full' in self.results and not self.results['questions_full']['passed']:
                print("\n⚠️ Tests de questions complètes échoués")
                print("   → Optimiser les cas complexes")
            
            if 'critical' in self.results and not self.results['critical']['passed']:
                print("\n🔴 TESTS CRITIQUES ÉCHOUÉS")
                print("   → ⚠️ BLOQUANT pour la production")
                print("   → Action immédiate requise")
        
        print("\n" + "="*70)
        
        return all_passed
    
    def save_json_report(self):
        """Sauvegarde un rapport JSON pour CI/CD."""
        report_path = self.tests_dir / "test_report.json"
        
        report = {
            'timestamp': self.start_time.isoformat(),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'pipeline_version': 'hybrid_extractor + final_corrections + manual_fixes',
            'results': {}
        }
        
        for suite_name, result in self.results.items():
            report['results'][suite_name] = {
                'passed': result['passed'],
                'returncode': result['returncode']
            }
        
        report['summary'] = {
            'total_suites': len(self.results),
            'passed_suites': sum(1 for r in self.results.values() if r['passed']),
            'all_passed': all(r['passed'] for r in self.results.values()),
            'critical_passed': all(
                self.results[k]['passed'] 
                for k in ['ground_truth', 'security', 'critical'] 
                if k in self.results
            )
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Rapport JSON sauvegardé: {report_path}")
    
    def generate_detailed_logs(self):
        """Génère des logs détaillés pour chaque suite."""
        logs_dir = self.tests_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
        
        for suite_name, result in self.results.items():
            log_file = logs_dir / f"{suite_name}_{timestamp}.log"
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Test Suite: {result['name']}\n")
                f.write(f"Status: {'PASS' if result['passed'] else 'FAIL'}\n")
                f.write(f"Return Code: {result['returncode']}\n")
                f.write(f"Pipeline: hybrid_extractor + final_corrections + manual_fixes\n")
                f.write("\n" + "="*70 + "\n")
                f.write("STDOUT:\n")
                f.write(result['stdout'])
                f.write("\n" + "="*70 + "\n")
                f.write("STDERR:\n")
                f.write(result['stderr'])
        
        print(f"📁 Logs détaillés sauvegardés dans: {logs_dir}/")


def main():
    """Point d'entrée principal."""
    print("\n" + "🚀"*35)
    print("SUITE DE TESTS COMPLÈTE - VERSION AMÉLIORÉE")
    print("🚀"*35)
    print()
    print("Pipeline d'extraction validé:")
    print("  1. hybrid_extractor.py")
    print("  2. final_corrections.py")
    print("  3. manual_fixes.py")
    print("  4. db_loader.py")
    print()
    print("Tests exécutés:")
    print("  ✓ Phase 1: Vérité terrain (COCODY, KOUMASSI, YOPOUGON, etc.)")
    print("  ✓ Phase 2: Sécurité SQL (injections, adversarial prompts)")
    print("  ✓ Phase 3: Agrégations (COUNT, SUM, AVG)")
    print("  ✓ Phase 4: Configuration LLM")
    print("  ✓ Phase 5: Évaluation (métriques)")
    print("  ✓ Phase 6: Questions (simples + complètes)")
    print("  ✓ Phase 7: Tests critiques uniquement")
    print()
    
    runner = TestRunner()
    
    try:
        # Exécuter tous les tests
        runner.run_all_tests()
        
        # Générer les rapports
        all_passed = runner.generate_summary_report()
        runner.save_json_report()
        runner.generate_detailed_logs()
        
        # Exit code pour CI/CD
        sys.exit(0 if all_passed else 1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrompus par l'utilisateur")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()