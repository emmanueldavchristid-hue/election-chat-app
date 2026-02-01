"""
Tracer - Système de traçabilité et observability
Log chaque étape : Intent → SQL → Validation → Execution → Response
"""
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from functools import wraps
import sys

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class RequestTracer:
    """
    Trace une requête utilisateur de bout en bout
    """
    
    def __init__(self, question: str, session_id: str = None):
        self.question = question
        self.session_id = session_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        self.trace_id = f"{self.session_id}_{int(time.time() * 1000)}"
        
        self.start_time = time.time()
        self.steps = []
        self.metrics = {
            'total_duration_ms': 0,
            'llm_calls': 0,
            'llm_tokens_input': 0,
            'llm_tokens_output': 0,
            'sql_queries': 0,
            'sql_duration_ms': 0,
        }
        self.error = None
        self.business_error = None
    
    def log_step(self, step_name: str, data: Dict[str, Any], duration_ms: float = None):
        """
        Log une étape du traitement
        
        Args:
            step_name: Nom de l'étape (ex: 'intent_classification', 'sql_generation')
            data: Données de l'étape
            duration_ms: Durée en millisecondes
        """
        step = {
            'step': step_name,
            'timestamp': datetime.now().isoformat(),
            'duration_ms': duration_ms,
            'data': data
        }
        self.steps.append(step)
    
    def log_llm_call(self, model: str, tokens_input: int, tokens_output: int, duration_ms: float):
        """Log un appel LLM"""
        self.metrics['llm_calls'] += 1
        self.metrics['llm_tokens_input'] += tokens_input
        self.metrics['llm_tokens_output'] += tokens_output
        
        self.log_step('llm_call', {
            'model': model,
            'tokens_input': tokens_input,
            'tokens_output': tokens_output
        }, duration_ms)
    
    def log_sql_query(self, sql: str, result_rows: int, duration_ms: float, success: bool = True):
        """Log une requête SQL"""
        self.metrics['sql_queries'] += 1
        self.metrics['sql_duration_ms'] += duration_ms
        
        self.log_step('sql_execution', {
            'sql': sql[:200],  # Tronquer si trop long
            'result_rows': result_rows,
            'success': success
        }, duration_ms)
    
    def log_chart_generation(self, chart_type: str, data_points: int, duration_ms: float):
        """Log la génération d'un graphique"""
        self.log_step('chart_generation', {
            'chart_type': chart_type,
            'data_points': data_points
        }, duration_ms)
    
    def log_fraud_analysis(self, anomalies_found: int, analysis_type: str, duration_ms: float):
        """Log une analyse de fraude"""
        self.log_step('fraud_analysis', {
            'anomalies_found': anomalies_found,
            'analysis_type': analysis_type
        }, duration_ms)
    
    def log_rag_search(self, query: str, results_found: int, duration_ms: float):
        """Log une recherche RAG"""
        self.log_step('rag_search', {
            'query': query[:100],
            'results_found': results_found
        }, duration_ms)
    
    def log_intent_classification(self, intent: str, confidence: float, duration_ms: float):
        """Log la classification d'intention"""
        self.log_step('intent_classification', {
            'intent': intent,
            'confidence': confidence
        }, duration_ms)

    def log_cache_hit(self, cache_type: str, question_original: str = None, similarity_score: float = None):
        """
        ✅ NOUVEAU : Log un cache hit
        
        Args:
            cache_type: 'exact_match' | 'similarity' | 'sql'
            question_original: Question originale (pour similarité)
            similarity_score: Score de similarité (0-1)
        """
        self.log_step('cache_hit', {
            'cache_type': cache_type,
            'question_original': question_original,
            'similarity_score': similarity_score
        }, 0)  # Cache = instantané
        
    def log_error(self, step_name: str, error_msg: str, error_type: str = None):
        """Log une erreur"""
        self.error = {
            'step': step_name,
            'message': error_msg,
            'type': error_type or 'unknown'
        }
        
        self.log_step('error', {
            'error_message': error_msg,
            'error_type': error_type
        })

    def log_business_error(self, error_type: str, description: str, sql: str = None):
        """
        ✅ NOUVEAU : Log une erreur métier (résultats vides, mauvaise interprétation)
        
        Args:
            error_type: Type d'erreur ('empty_result', 'ambiguous', 'wrong_interpretation')
            description: Description de l'erreur
            sql: SQL qui a causé l'erreur (optionnel)
        """
        self.business_error = {
            'type': error_type,
            'description': description,
            'sql': sql[:200] if sql else None
        }
        
        self.log_step('business_error', {
            'error_type': error_type,
            'description': description
        })
    
    def finalize(self) -> Dict[str, Any]:
        """Finalise la trace et retourne le résumé"""
        self.metrics['total_duration_ms'] = (time.time() - self.start_time) * 1000
        
        return {
            'trace_id': self.trace_id,
            'session_id': self.session_id,
            'question': self.question,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'metrics': self.metrics,
            'steps': self.steps,
            'error': self.error,
            'business_error': self.business_error,  # ✅ AJOUTÉ
            'success': self.error is None and self.business_error is None  # ✅ MODIFIÉ
        }
    
    
    def save_to_file(self, output_dir: Path = None):
        """Sauvegarde la trace dans un fichier JSON"""
        if output_dir is None:
            output_dir = Path('data/traces')
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        trace = self.finalize()
        
        filename = f"{self.trace_id}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trace, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def print_summary(self):
        """Affiche un résumé de la trace"""
        trace = self.finalize()
        
        print("\n" + "="*70)
        print(f"📊 TRACE SUMMARY - {trace['trace_id']}")
        print("="*70)
        
        print(f"\n❓ Question: {self.question}")
        print(f"⏱️ Total Duration: {trace['metrics']['total_duration_ms']:.2f}ms")
        print(f"✅ Success: {trace['success']}")
        
        print("\n📈 Metrics:")
        print(f"   - LLM Calls: {trace['metrics']['llm_calls']}")
        print(f"   - LLM Tokens (in): {trace['metrics']['llm_tokens_input']}")
        print(f"   - LLM Tokens (out): {trace['metrics']['llm_tokens_output']}")
        print(f"   - SQL Queries: {trace['metrics']['sql_queries']}")
        print(f"   - SQL Duration: {trace['metrics']['sql_duration_ms']:.2f}ms")
        
        print("\n📝 Steps:")
        for i, step in enumerate(trace['steps'], 1):
            duration = f"{step['duration_ms']:.2f}ms" if step['duration_ms'] else "N/A"
            print(f"   {i}. {step['step']} - {duration}")
        
        if trace['error']:
            print(f"\n❌ Error: {trace['error']['message']}")
        
        print("="*70)


class TracerManager:
    """Gestionnaire global des traces"""
    
    def __init__(self, log_dir: Path = None):
        if log_dir is None:
            log_dir = Path('data/traces')
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Logger Python standard
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Configure le logger Python"""
        logger = logging.getLogger('election_chat_tracer')
        logger.setLevel(logging.INFO)
        
        # Handler fichier
        log_file = self.log_dir / 'application.log'
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        
        # Handler console
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def create_tracer(self, question: str, session_id: str = None) -> RequestTracer:
        """Crée un nouveau tracer pour une requête"""
        return RequestTracer(question, session_id)
    
    def get_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère les traces récentes"""
        trace_files = sorted(
            self.log_dir.glob('*.json'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]
        
        traces = []
        for file in trace_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    traces.append(json.load(f))
            except Exception as e:
                self.logger.error(f"Error loading trace {file}: {e}")
        
        return traces
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Génère un résumé des métriques"""
        traces = self.get_traces(limit=1000)
        
        if not traces:
            return {}
        
        total_requests = len(traces)
        
        # ✅ MODIFIÉ : Prendre en compte les business_errors
        successful_requests = sum(
            1 for t in traces 
            if t['success'] and not t.get('business_error')  # ✅ Ajouté
        )
        
        technical_errors = sum(1 for t in traces if t.get('error'))
        business_errors = sum(1 for t in traces if t.get('business_error'))
        
        failed_requests = technical_errors + business_errors
        
        avg_duration = sum(t['metrics']['total_duration_ms'] for t in traces) / total_requests
        avg_llm_calls = sum(t['metrics']['llm_calls'] for t in traces) / total_requests
        total_llm_tokens = sum(
            t['metrics']['llm_tokens_input'] + t['metrics']['llm_tokens_output']
            for t in traces
        )
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'technical_errors': technical_errors,  # ✅ NOUVEAU
            'business_errors': business_errors,    # ✅ NOUVEAU
            'success_rate': successful_requests / total_requests * 100,
            'avg_duration_ms': avg_duration,
            'avg_llm_calls_per_request': avg_llm_calls,
            'total_llm_tokens': total_llm_tokens,
            'avg_tokens_per_request': total_llm_tokens / total_requests
        }
    
    def export_metrics_csv(self, output_file: Path = None):
        """Exporte les métriques en CSV pour analyse Excel/Pandas"""
        if output_file is None:
            output_file = self.log_dir / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        traces = self.get_traces(limit=10000)
        
        if not traces:
            print("⚠️ Aucune trace à exporter")
            return None
        
        # Créer DataFrame avec pandas
        try:
            import pandas as pd
            
            data = []
            for trace in traces:
                data.append({
                    'trace_id': trace['trace_id'],
                    'question': trace['question'][:100],  # Tronquer
                    'success': trace['success'],
                    'duration_ms': trace['metrics']['total_duration_ms'],
                    'llm_calls': trace['metrics']['llm_calls'],
                    'llm_tokens_input': trace['metrics']['llm_tokens_input'],
                    'llm_tokens_output': trace['metrics']['llm_tokens_output'],
                    'llm_tokens_total': trace['metrics']['llm_tokens_input'] + trace['metrics']['llm_tokens_output'],
                    'sql_queries': trace['metrics']['sql_queries'],
                    'sql_duration_ms': trace['metrics']['sql_duration_ms'],
                    'timestamp': trace['start_time'],
                    'error': trace.get('error', {}).get('message', '') if trace.get('error') else ''
                })
            
            df = pd.DataFrame(data)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            print(f"✅ Métriques exportées: {output_file}")
            print(f"📊 {len(df)} traces exportées")
            
            return output_file
            
        except ImportError:
            print("⚠️ pandas non installé, export CSV impossible")
            return None
        except Exception as e:
            self.logger.error(f"Erreur export CSV: {e}")
            return None
    
    def get_performance_report(self) -> str:
        """Génère un rapport de performance textuel"""
        metrics = self.get_metrics_summary()
        
        if not metrics:
            return "❌ Aucune métrique disponible"
        
        report = []
        report.append("="*70)
        report.append("📊 RAPPORT DE PERFORMANCE")
        report.append("="*70)
        report.append(f"\n📈 Requêtes:")
        report.append(f"   - Total: {metrics['total_requests']}")
        report.append(f"   - Succès: {metrics['successful_requests']} ({metrics['success_rate']:.1f}%)")
        report.append(f"   - Échecs: {metrics['failed_requests']}")
        report.append(f"     • Erreurs techniques: {metrics.get('technical_errors', 0)}")  # ✅ NOUVEAU
        report.append(f"     • Erreurs métier: {metrics.get('business_errors', 0)}")      # ✅ NOUVEAU
        
        report.append(f"\n⏱️ Performance:")
        report.append(f"   - Durée moyenne: {metrics['avg_duration_ms']:.0f}ms")
        report.append(f"   - Appels LLM/requête: {metrics['avg_llm_calls_per_request']:.1f}")
        
        report.append(f"\n🤖 LLM:")
        report.append(f"   - Tokens totaux: {metrics['total_llm_tokens']:,}")
        report.append(f"   - Tokens/requête: {metrics['avg_tokens_per_request']:.0f}")
        
        # Estimation coût (si Anthropic)
        cost_per_1k_input = 0.003  # $3/M tokens input
        cost_per_1k_output = 0.015  # $15/M tokens output
        estimated_cost = (metrics['total_llm_tokens'] / 1000) * cost_per_1k_input
        report.append(f"   - Coût estimé: ${estimated_cost:.4f} (si Anthropic)")
        
        report.append("="*70)
        
        return "\n".join(report)


def trace_function(step_name: str):
    """
    Décorateur pour tracer automatiquement une fonction
    
    Usage:
        @trace_function('sql_generation')
        def generate_sql(question):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                
                # Si la fonction retourne un dict avec 'tracer', on log
                if isinstance(result, dict) and 'tracer' in kwargs:
                    tracer: RequestTracer = kwargs['tracer']
                    tracer.log_step(step_name, {'success': True}, duration_ms)
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                
                if 'tracer' in kwargs:
                    tracer: RequestTracer = kwargs['tracer']
                    tracer.log_error(step_name, str(e), type(e).__name__)
                
                raise
        
        return wrapper
    return decorator


def main():
    """Test du tracer"""
    
    print("="*70)
    print("🧪 TEST TRACER")
    print("="*70)
    
    # Créer un tracer
    tracer = RequestTracer("Combien de sièges a gagné le RHDP ?")
    
    # Simuler des étapes
    time.sleep(0.05)
    tracer.log_step('intent_classification', {
        'intent': 'sql_query',
        'confidence': 0.95
    }, 50)
    
    time.sleep(0.1)
    tracer.log_llm_call('llama3.1', tokens_input=150, tokens_output=80, duration_ms=100)
    
    time.sleep(0.03)
    tracer.log_step('sql_validation', {
        'valid': True,
        'sanitized': True
    }, 30)
    
    time.sleep(0.02)
    tracer.log_sql_query(
        "SELECT COUNT(*) FROM elections WHERE parti = 'RHDP' AND elu = TRUE",
        result_rows=1,
        duration_ms=20,
        success=True
    )
    
    time.sleep(0.08)
    tracer.log_llm_call('llama3.1', tokens_input=200, tokens_output=120, duration_ms=80)
    
    # Afficher résumé
    tracer.print_summary()
    
    # Sauvegarder
    filepath = tracer.save_to_file()
    print(f"\n💾 Trace sauvegardée: {filepath}")
    
    # Test TracerManager
    print("\n" + "="*70)
    print("🧪 TEST TRACER MANAGER")
    print("="*70)
    
    manager = TracerManager()
    
    # Créer plusieurs traces
    for i in range(3):
        t = manager.create_tracer(f"Question {i+1}")
        t.log_step('test', {'index': i}, 10)
        t.save_to_file()
    
    # Récupérer métriques
    metrics = manager.get_metrics_summary()
    
    print("\n📊 Métriques globales:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"   - {key}: {value:.2f}")
        else:
            print(f"   - {key}: {value}")


if __name__ == "__main__":
    main()