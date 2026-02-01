"""
Query Executor - Safely executes SQL queries against DuckDB.
✅ AVEC CACHE - Optimisé pour performances
"""
import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
import signal
from contextlib import contextmanager
import json

# ✅ NOUVEAU
from src.utils.cache_manager import CacheManager


class TimeoutException(Exception):
    """Exception raised when query times out."""
    pass


@contextmanager
def timeout(seconds: int):
    """Context manager for query timeout."""
    def signal_handler(signum, frame):
        raise TimeoutException(f"Query timed out after {seconds} seconds")
    
    # Set signal handler (Unix only, Windows will skip)
    try:
        old_handler = signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    except AttributeError:
        # Windows doesn't support SIGALRM, just execute without timeout
        yield


class QueryExecutor:
    """
    Execute SQL queries safely.
    
    ✅ NOUVEAU : Intégration cache pour requêtes répétitives
    """
    
    def __init__(self, db_path: Path, timeout_seconds: int = 30, enable_cache: bool = True, cache_ttl: int = 3600):
        """
        Initialize executor.
        
        Args:
            db_path: Chemin vers base DuckDB
            timeout_seconds: Timeout par défaut
            enable_cache: Activer cache SQL (défaut: True)
            cache_ttl: Durée validité cache en secondes (défaut: 1h)
        """
        self.db_path = db_path
        self.timeout_seconds = timeout_seconds
        self.conn = None
        
        # ✅ NOUVEAU : Cache Manager
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.cache_manager = CacheManager() if enable_cache else None
    
    def connect(self):
        """Connect to database."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        self.conn = duckdb.connect(str(self.db_path), read_only=True)
        
        # ✅ NOUVEAU : Log cache status
        if self.enable_cache and self.cache_manager:
            stats = self.cache_manager.get_cache_stats()
            print(f"💾 Query cache: {stats['sql_count']} requêtes cachées")
    
    def execute(self, sql: str) -> Dict[str, Any]:
        """
        Execute SQL query and return results.
        
        ✅ NOUVEAU : Vérifie cache avant exécution
        
        Returns:
            Dict with 'success', 'data', 'row_count', 'columns', and optional 'error'
        """
        if not self.conn:
            self.connect()
        
        # ✅ NOUVEAU : Cache lookup
        if self.enable_cache and self.cache_manager:
            cached_result = self.cache_manager.get_cached_sql_result(sql)
            
            if cached_result is not None:
                # Reconstruire DataFrame depuis cache
                try:
                    data = pd.DataFrame(cached_result['data'])
                    
                    return {
                        'success': True,
                        'data': data,
                        'row_count': cached_result['row_count'],
                        'columns': cached_result['columns'],
                        'sql': sql,
                        'cached': True  # ✅ Indicateur cache hit
                    }
                except Exception as e:
                    # Cache corrompu, continuer sans cache
                    print(f"⚠️ Cache corrompu, exécution SQL: {e}")
        
        # Exécution normale
        try:
            # Execute with timeout protection (Unix only)
            with timeout(self.timeout_seconds):
                result = self.conn.execute(sql).fetchdf()
            
            query_result = {
                'success': True,
                'data': result,
                'row_count': len(result),
                'columns': list(result.columns),
                'sql': sql,
                'cached': False  # ✅ Pas de cache
            }
            
            # ✅ NOUVEAU : Cacher résultat si activé
            if self.enable_cache and self.cache_manager:
                # Convertir DataFrame en dict pour sérialisation JSON
                cache_data = {
                    'data': result.to_dict('records'),
                    'row_count': len(result),
                    'columns': list(result.columns)
                }
                
                try:
                    self.cache_manager.cache_sql_result(sql, cache_data, ttl_seconds=self.cache_ttl)
                except Exception as e:
                    # Échec cache non-bloquant
                    print(f"⚠️ Impossible de cacher résultat SQL: {e}")
            
            return query_result
            
        except TimeoutException as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'timeout',
                'sql': sql,
                'cached': False
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'execution_error',
                'sql': sql,
                'cached': False
            }
    
    def format_result(self, result: Dict[str, Any], max_rows: int = 10) -> str:
        """
        Format query result as human-readable text.
        
        ✅ NOUVEAU : Affiche indicateur cache
        """
        if not result['success']:
            return f"❌ Query failed: {result.get('error', 'Unknown error')}"
        
        data = result['data']
        row_count = result['row_count']
        
        # ✅ NOUVEAU : Badge cache
        cache_badge = " 💾 (cached)" if result.get('cached') else ""
        
        if row_count == 0:
            return f"📊 No results found.{cache_badge}"
        
        # Format as markdown table
        output = f"📊 Found {row_count} result(s){cache_badge}\n\n"
        
        # Show top rows as table
        preview = data.head(max_rows)
        output += preview.to_markdown(index=False)
        
        if row_count > max_rows:
            output += f"\n\n... and {row_count - max_rows} more row(s)"
        
        return output
    
    def get_summary(self, result: Dict[str, Any]) -> str:
        """
        Get a natural language summary of the result.
        """
        if not result['success']:
            return f"The query failed: {result.get('error', 'Unknown error')}"
        
        data = result['data']
        row_count = result['row_count']
        
        if row_count == 0:
            return "No results were found for this query."
        
        # Simple summaries based on result structure
        if row_count == 1 and len(data.columns) == 1:
            # Single value result (like COUNT)
            value = data.iloc[0, 0]
            return f"The result is: {value}"
        
        if 'seats' in str(data.columns).lower() or 'sieges' in str(data.columns).lower():
            return f"Found {row_count} result(s) showing seat counts."
        
        if 'candidate' in str(data.columns).lower() or 'candidat' in str(data.columns).lower():
            return f"Found {row_count} candidate(s) matching your query."
        
        return f"The query returned {row_count} result(s)."
    
    # ✅ NOUVEAU : Méthodes de gestion cache
    def clear_cache(self) -> int:
        """Vide le cache SQL"""
        if self.cache_manager:
            count = self.cache_manager.clear_sql_cache()
            print(f"🗑️ {count} requêtes SQL supprimées du cache")
            return count
        return 0
    
    def get_cache_stats(self) -> dict:
        """Stats du cache"""
        if self.cache_manager:
            return self.cache_manager.get_cache_stats()
        return {}
    
    def set_cache_ttl(self, ttl_seconds: int):
        """Change le TTL du cache"""
        self.cache_ttl = ttl_seconds
        print(f"✅ Cache TTL mis à jour : {ttl_seconds}s")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


def main():
    """Test executor avec démonstration cache."""
    from src.utils.config import DB_PATH
    import time
    
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run: python -m src.ingestion.db_loader")
        return
    
    executor = QueryExecutor(DB_PATH, enable_cache=True, cache_ttl=300)  # 5 min TTL
    
    test_queries = [
        "SELECT COUNT(*) as total_seats FROM election_results WHERE elu = TRUE",
        "SELECT parti_normalise, COUNT(*) as seats FROM election_results WHERE elu = TRUE GROUP BY parti_normalise ORDER BY seats DESC LIMIT 5",
        "SELECT candidat_normalise, voix FROM election_results ORDER BY voix DESC LIMIT 10",
    ]
    
    print("="*70)
    print("🧪 TESTING QUERY EXECUTOR - AVEC CACHE")
    print("="*70)
    
    try:
        # Premier passage (sans cache)
        print("\n🔄 PREMIER PASSAGE (Sans cache)")
        start = time.time()
        
        for i, sql in enumerate(test_queries, 1):
            print(f"\n📝 Query {i}: {sql[:60]}...")
            result = executor.execute(sql)
            
            if result['success']:
                cached = "💾 CACHED" if result.get('cached') else "🔍 EXECUTED"
                print(f"✅ {cached} ({result['row_count']} rows)")
            else:
                print(f"❌ Failed: {result['error']}")
        
        duration_1 = time.time() - start
        print(f"\n⏱️ Durée totale: {duration_1:.3f}s")
        
        # Deuxième passage (avec cache)
        print("\n" + "="*70)
        print("🚀 DEUXIÈME PASSAGE (Avec cache)")
        start = time.time()
        
        for i, sql in enumerate(test_queries, 1):
            print(f"\n📝 Query {i}: {sql[:60]}...")
            result = executor.execute(sql)
            
            if result['success']:
                cached = "💾 CACHED" if result.get('cached') else "🔍 EXECUTED"
                print(f"✅ {cached} ({result['row_count']} rows)")
            else:
                print(f"❌ Failed: {result['error']}")
        
        duration_2 = time.time() - start
        print(f"\n⏱️ Durée totale: {duration_2:.3f}s")
        
        # Comparaison
        speedup = duration_1 / duration_2 if duration_2 > 0 else 1
        print("\n" + "="*70)
        print(f"📊 GAIN DE PERFORMANCE : {speedup:.1f}x plus rapide avec cache")
        print("="*70)
        
        # Stats
        stats = executor.get_cache_stats()
        print(f"\n💾 Cache stats: {stats}")
    
    finally:
        executor.close()


if __name__ == "__main__":
    main()