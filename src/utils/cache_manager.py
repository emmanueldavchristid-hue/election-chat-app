"""
CACHE MANAGER V2.2 - Performance optimization multicouche
✅ OPTIMISÉ : Chargement LAZY du modèle (évite 7x chargements!)
✅ CORRIGÉ : Vérification intent pour éviter faux positifs (89% "histogramme" vs "combien")

Cache embeddings, SQL results, questions, similarité sémantique

Performance attendue : 50-80% des questions répétées instantanées ⚡
"""

import hashlib
import json
import pickle
import time
from pathlib import Path
from typing import Any, Optional, Dict, List, Tuple
import logging
import difflib

logger = logging.getLogger(__name__)


class CacheManager:
    """Gestionnaire de cache multicouche pour optimiser performances"""
    
    # ✅ SINGLETON pour éviter multiples chargements
    _instance = None
    _model = None
    _model_loaded = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, cache_dir: Path = Path("data/cache")):
        # Éviter réinitialisation si déjà fait
        if hasattr(self, '_initialized'):
            return
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Sous-dossiers
        self.embeddings_dir = self.cache_dir / "embeddings"
        self.sql_dir = self.cache_dir / "sql_results"
        self.pdf_versions_dir = self.cache_dir / "pdf_versions"
        self.questions_dir = self.cache_dir / "questions"
        self.metrics_file = self.cache_dir / "metrics.json"
        
        for d in [self.embeddings_dir, self.sql_dir, self.pdf_versions_dir, self.questions_dir]:
            d.mkdir(exist_ok=True)
        
        # Métriques cache
        self.metrics = self._load_metrics()
        
        # ✅ NE PAS charger le modèle ici - on le fera LAZY
        self.similarity_enabled = False
        
        logger.info(f"✅ Cache Manager V2.2 initialisé : {cache_dir}")
        logger.info("💡 Modèle sentence-transformers sera chargé à la demande (lazy loading)")
        
        self._initialized = True
    
    def _load_model_lazy(self):
        """✅ NOUVEAU : Charge le modèle SEULEMENT quand nécessaire"""
        if CacheManager._model_loaded:
            return CacheManager._model is not None
        
        try:
            print("📥 Chargement du modèle sentence-transformers (1ère fois uniquement)...")
            from sentence_transformers import SentenceTransformer
            CacheManager._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            CacheManager._model_loaded = True
            self.similarity_enabled = True
            print("✅ Modèle chargé avec succès!")
            logger.info("✅ Similarité sémantique activée (sentence-transformers)")
            return True
        except ImportError:
            CacheManager._model_loaded = True
            CacheManager._model = None
            self.similarity_enabled = False
            print("⚠️  sentence-transformers non disponible. Utilisation de difflib uniquement.")
            logger.info("⚠️ sentence-transformers non disponible. Utilisation de difflib uniquement.")
            return False
    
    # ========================================================================
    # MÉTRIQUES CACHE
    # ========================================================================
    
    def _load_metrics(self) -> Dict[str, int]:
        """Charge les métriques depuis le fichier"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'questions_hits': 0,
            'questions_miss': 0,
            'similarity_hits': 0,
            'similarity_miss': 0,
            'sql_hits': 0,
            'sql_miss': 0,
            'total_requests': 0
        }
    
    def _save_metrics(self):
        """Sauvegarde les métriques"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache metrics: {e}")
    
    def _record_hit(self, cache_type: str):
        """Enregistre un cache hit"""
        self.metrics[f'{cache_type}_hits'] += 1
        self.metrics['total_requests'] += 1
        self._save_metrics()
    
    def _record_miss(self, cache_type: str):
        """Enregistre un cache miss"""
        self.metrics[f'{cache_type}_miss'] += 1
        self.metrics['total_requests'] += 1
        self._save_metrics()
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Récupère métriques cache complètes"""
        
        total_hits = (self.metrics['questions_hits'] + 
                     self.metrics['similarity_hits'] + 
                     self.metrics['sql_hits'])
        
        total_miss = (self.metrics['questions_miss'] + 
                     self.metrics['similarity_miss'] + 
                     self.metrics['sql_miss'])
        
        total_requests = self.metrics['total_requests']
        
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'questions_hits': self.metrics['questions_hits'],
            'questions_miss': self.metrics['questions_miss'],
            'similarity_hits': self.metrics['similarity_hits'],
            'similarity_miss': self.metrics['similarity_miss'],
            'sql_hits': self.metrics['sql_hits'],
            'sql_miss': self.metrics['sql_miss'],
            'total_hits': total_hits,
            'total_miss': total_miss,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'questions_cached': len(list(self.questions_dir.glob("*.json"))),
            'embeddings_cached': len(list(self.embeddings_dir.glob("*.pkl"))),
            'sql_cached': len(list(self.sql_dir.glob("*.json")))
        }
    
    # ========================================================================
    # LAYER 1 : CACHE QUESTIONS EXACT MATCH
    # ========================================================================
    
    def _normalize_question(self, question: str) -> str:
        """Normalise question pour matching exact"""
        return ' '.join(question.lower().strip().split())
    
    def _get_question_hash(self, question: str) -> str:
        """Hash pour question normalisée"""
        normalized = self._normalize_question(question)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def cache_question_response(
        self, 
        question: str, 
        response: str, 
        data: Any = None, 
        sql: str = None,
        intent: str = None,
        metadata: Dict = None
    ) -> None:
        """Cache une paire question/réponse complète"""
        
        question_hash = self._get_question_hash(question)
        cache_file = self.questions_dir / f"{question_hash}.json"
        
        cache_data = {
            'question': question,
            'question_normalized': self._normalize_question(question),
            'response': response,
            'sql': sql,
            'intent': intent,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        
        # Convertir data en dict si DataFrame
        if data is not None:
            try:
                if hasattr(data, 'to_dict'):  # pandas DataFrame
                    # ✅ NOUVEAU : Convertir int64/float64 en Python natif
                    import numpy as np
                    
                    # Copier le DataFrame pour ne pas modifier l'original
                    data_copy = data.copy()
                    
                    # Convertir toutes les colonnes numériques
                    for col in data_copy.columns:
                        if data_copy[col].dtype == 'int64':
                            data_copy[col] = data_copy[col].astype(int)
                        elif data_copy[col].dtype == 'float64':
                            data_copy[col] = data_copy[col].astype(float)
                        # Remplacer NaN par None (JSON-compatible)
                        elif data_copy[col].dtype == 'object':
                            data_copy[col] = data_copy[col].where(pd.notna(data_copy[col]), None)
                    
                    cache_data['data'] = data_copy.to_dict('records')
                    cache_data['data_columns'] = list(data.columns)
                else:
                    cache_data['data'] = data
            except Exception as e:
                logger.warning(f"Failed to cache data: {e}")
                print(f"Failed to cache question: {e}")  # ✅ Afficher l'erreur
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Question cachée: {question[:50]}... (intent: {intent})")
            logger.debug(f"✅ Question cached: {question[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to cache question: {e}")
    
    def get_cached_question_response(self, question: str) -> Optional[Dict[str, Any]]:
        """Récupère réponse cachée pour question exacte"""
        
        question_hash = self._get_question_hash(question)
        cache_file = self.questions_dir / f"{question_hash}.json"
        
        if not cache_file.exists():
            self._record_miss('questions')
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Vérifier TTL (24h par défaut)
            elapsed = time.time() - cache_data['timestamp']
            if elapsed > 86400:  # 24 heures
                logger.debug(f"Question cache expired: {question[:50]}...")
                cache_file.unlink()
                self._record_miss('questions')
                return None
            
            self._record_hit('questions')
            print(f"✅ CACHE HIT EXACT! {question[:50]}...")
            logger.debug(f"✅ Question cache HIT: {question[:50]}...")
            
            return {
                'response': cache_data['response'],
                'data': cache_data.get('data'),
                'data_columns': cache_data.get('data_columns'),
                'sql': cache_data.get('sql'),
                'intent': cache_data.get('intent'),
                'metadata': cache_data.get('metadata', {}),
                'cached': True,
                'cache_type': 'exact_match'
            }
        
        except Exception as e:
            logger.warning(f"Failed to load cached question: {e}")
            self._record_miss('questions')
            return None
    
    # ========================================================================
    # LAYER 2 : SIMILARITÉ SÉMANTIQUE
    # ========================================================================
    
    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """Calcule similarité entre deux textes"""
        
        # ✅ Charger modèle LAZY
        if not CacheManager._model_loaded:
            self._load_model_lazy()
        
        if self.similarity_enabled and CacheManager._model is not None:
            # Utiliser embeddings sémantiques
            try:
                emb1 = CacheManager._model.encode(text1, convert_to_numpy=True)
                emb2 = CacheManager._model.encode(text2, convert_to_numpy=True)
                
                # Similarité cosinus
                import numpy as np
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                return float(similarity)
            except Exception as e:
                logger.warning(f"Embedding similarity failed: {e}")
        
        # Fallback : difflib
        return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def find_similar_question(
        self, 
        question: str, 
        threshold: float = 0.95  # ✅ CORRIGÉ : Monté à 95% (était 85%)
    ) -> Optional[Tuple[str, Dict[str, Any], float]]:
        """
        Trouve question similaire dans le cache
        
        ✅ CORRIGÉ : Bloque les intents incompatibles (chart ne peut pas matcher sql_query)
        """
        
        normalized_question = self._normalize_question(question)
        
        best_match = None
        best_score = 0.0
        best_data = None
        
        # Parcourir toutes les questions cachées
        for cache_file in self.questions_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Vérifier TTL
                elapsed = time.time() - cache_data['timestamp']
                if elapsed > 86400:  # 24h
                    continue
                
                cached_question_normalized = cache_data['question_normalized']
                
                # Calculer similarité
                score = self._compute_text_similarity(normalized_question, cached_question_normalized)
                
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = cache_data['question']
                    
                    # ✅ NOUVEAU : Vérifier que l'intent est compatible
                    cached_intent = cache_data.get('intent')
                    
                    best_data = {
                        'response': cache_data['response'],
                        'data': cache_data.get('data'),
                        'data_columns': cache_data.get('data_columns'),
                        'sql': cache_data.get('sql'),
                        'intent': cached_intent,  # ✅ Inclure l'intent
                        'metadata': cache_data.get('metadata', {}),
                        'cached': True,
                        'cache_type': 'similarity',
                        'similarity_score': score,
                        'original_question': cache_data['question']
                    }
            
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")
                continue
        
        if best_match:
            # ✅ NOUVEAU : Vérifier l'intent avant de retourner
            # Si l'intent du cache ne correspond pas, ignorer
            cached_intent = best_data.get('intent')
            
            # Intents compatibles : sql_query peut matcher avec sql_query uniquement
            # chart ne peut PAS matcher avec sql_query, etc.
            if cached_intent in ['chart', 'conversation', 'off_topic']:
                # Ces intents sont trop spécifiques, ne pas réutiliser
                print(f"⚠️  Question similaire trouvée mais intent incompatible: {cached_intent} (score: {best_score:.0%})")
                print(f"   → Question actuelle nécessite un traitement différent")
                self._record_miss('similarity')
                return None
            
            self._record_hit('similarity')
            print(f"✅ CACHE HIT SIMILAIRE ({best_score:.0%}): {best_match[:50]}...")
            logger.debug(f"✅ Similar question found ({best_score:.2f}): {best_match[:50]}...")
            return (best_match, best_data, best_score)
        
        self._record_miss('similarity')
        return None
    
    # ========================================================================
    # PDF VERSIONING (inchangé)
    # ========================================================================
    
    def get_pdf_hash(self, pdf_path: Path) -> str:
        """Calcule hash SHA256 du PDF pour versioning"""
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        sha256_hash = hashlib.sha256()
        
        with open(pdf_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    # ========================================================================
    # EMBEDDINGS CACHE (inchangé)
    # ========================================================================
    
    def _get_text_hash(self, text: str) -> str:
        """Hash court pour texte"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def cache_embedding(self, text: str, embedding: Any) -> None:
        """Cache un embedding pour un texte"""
        
        text_hash = self._get_text_hash(text)
        cache_file = self.embeddings_dir / f"{text_hash}.pkl"
        
        with open(cache_file, "wb") as f:
            pickle.dump({"text": text, "embedding": embedding}, f)
    
    def get_cached_embedding(self, text: str) -> Optional[Any]:
        """Récupère embedding caché"""
        
        text_hash = self._get_text_hash(text)
        cache_file = self.embeddings_dir / f"{text_hash}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "rb") as f:
                data = pickle.load(f)
                return data["embedding"]
        except Exception as e:
            logger.warning(f"Failed to load cached embedding: {e}")
            return None
    
    # ========================================================================
    # SQL RESULTS CACHE (inchangé)
    # ========================================================================
    
    def cache_sql_result(self, sql: str, result: Any, ttl_seconds: int = 3600) -> None:
        """Cache résultat SQL avec TTL"""
        
        sql_hash = hashlib.md5(sql.encode('utf-8')).hexdigest()
        cache_file = self.sql_dir / f"{sql_hash}.json"
        
        cache_data = {
            "sql": sql,
            "result": result,
            "timestamp": time.time(),
            "ttl": ttl_seconds
        }
        
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    
    def get_cached_sql_result(self, sql: str) -> Optional[Any]:
        """Récupère résultat SQL caché si valide"""
        
        sql_hash = hashlib.md5(sql.encode('utf-8')).hexdigest()
        cache_file = self.sql_dir / f"{sql_hash}.json"
        
        if not cache_file.exists():
            self._record_miss('sql')
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            elapsed = time.time() - cache_data["timestamp"]
            
            if elapsed > cache_data["ttl"]:
                logger.debug(f"SQL cache expired for: {sql[:50]}...")
                cache_file.unlink()
                self._record_miss('sql')
                return None
            
            self._record_hit('sql')
            logger.debug(f"✅ SQL cache HIT: {sql[:50]}...")
            return cache_data["result"]
        
        except Exception as e:
            logger.warning(f"Failed to load cached SQL result: {e}")
            self._record_miss('sql')
            return None
    
    # ========================================================================
    # INVALIDATION
    # ========================================================================
    
    def clear_questions_cache(self) -> int:
        """Vide cache questions"""
        
        count = 0
        for f in self.questions_dir.glob("*.json"):
            f.unlink()
            count += 1
        
        logger.info(f"🗑️ Cleared {count} cached questions")
        return count
    
    def clear_embeddings_cache(self) -> int:
        """Vide cache embeddings"""
        
        count = 0
        for f in self.embeddings_dir.glob("*.pkl"):
            f.unlink()
            count += 1
        
        logger.info(f"🗑️ Cleared {count} cached embeddings")
        return count
    
    def clear_sql_cache(self) -> int:
        """Vide cache SQL"""
        
        count = 0
        for f in self.sql_dir.glob("*.json"):
            f.unlink()
            count += 1
        
        logger.info(f"🗑️ Cleared {count} cached SQL results")
        return count
    
    def clear_all_cache(self) -> dict:
        """Vide tout le cache"""
        
        return {
            "questions": self.clear_questions_cache(),
            "embeddings": self.clear_embeddings_cache(),
            "sql": self.clear_sql_cache()
        }
    
    def get_cache_stats(self) -> dict:
        """Stats sur le cache"""
        
        return {
            "questions_count": len(list(self.questions_dir.glob("*.json"))),
            "embeddings_count": len(list(self.embeddings_dir.glob("*.pkl"))),
            "sql_count": len(list(self.sql_dir.glob("*.json"))),
            "pdf_versions": len(list(self.pdf_versions_dir.glob("*.json")))
        }