"""
RAG Indexer HYBRID - CORRIGÉ
✅ FIX CRITIQUE: Recherche de régions fonctionne correctement
✅ FIX: Alias 'lagunes' → recherche dans RÉGIONS, pas circonscriptions
✅ FIX: Meilleure détection du type d'entité recherché
"""
import pandas as pd
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
import hashlib
import re

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import DB_PATH
from src.agent.query_executor import QueryExecutor
from src.utils.cache_manager import CacheManager

# Import ChromaDB si disponible
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = False  
except ImportError:
    CHROMADB_AVAILABLE = False


class RAGIndexerHybrid:
    """
    Stratégie HYBRIDE : Combine le meilleur des deux mondes
    - difflib : Précis pour fautes d'orthographe (Tiapum → Tiapoum)
    - ChromaDB : Meilleur pour recherche sémantique
    
    ✅ CORRIGÉ : Recherche de régions fonctionne maintenant
    """
    
    def __init__(self, persist_directory: str = "data/chromadb", enable_cache: bool = True):
        self.executor = QueryExecutor(DB_PATH)
        self.executor.connect()
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Cache Manager
        self.enable_cache = enable_cache
        self.cache_manager = CacheManager() if enable_cache else None
        
        # Dictionnaires d'aliases
        self.locality_aliases = self._build_locality_aliases()
        self.party_aliases = self._build_party_aliases()
        
        # Modes disponibles
        self.use_chromadb = CHROMADB_AVAILABLE
        
        # Collections ChromaDB
        self.client = None
        self.collections = {}
        
        # Index difflib (toujours chargés)
        self.difflib_data = {
            'circonscriptions': [],
            'candidats': [],
            'partis': [],
            'regions': []
        }
        
        # Initialiser
        self._initialize()
    
    def _build_locality_aliases(self) -> Dict[str, str]:
        """
        Construit un dictionnaire d'aliases pour localités
        
        ✅ CORRIGÉ : Séparation claire entre régions et circonscriptions
        """
        return {
            # COMMUNES D'ABIDJAN
            'yop': 'yopougon',
            'yopou': 'yopougon',
            'adjamé': 'adjame',
            'atti': 'attecoube',
            'atté': 'attecoube',
            'cocode': 'cocody',
            'coco': 'cocody',
            'plateau': 'plateau',
            'treich': 'treichville',
            'marko': 'marcory',
            'marco': 'marcory',
            'port': 'port-bouet',
            'portbouet': 'port-bouet',
            'porto': 'port-bouet',
            'koumassi': 'koumassi',
            'abobo': 'abobo',
            
            # GRANDES VILLES (CIRCONSCRIPTIONS)
            'bouaké': 'bouake',
            'bouake': 'bouake',
            'bké': 'bouake',
            'bke': 'bouake',
            'yamou': 'yamoussoukro',
            'yam': 'yamoussoukro',
            'daloa': 'daloa',
            'korogo': 'korhogo',
            'korhogo': 'korhogo',
            'koro': 'korhogo',
            'san': 'san-pedro',
            'sanpedro': 'san-pedro',
            'sp': 'san-pedro',
            'man': 'man',
            'gagnoa': 'gagnoa',
            'divo': 'divo',
            'abengourou': 'abengourou',
            'aben': 'abengourou',
            'soubré': 'soubre',
            'soubre': 'soubre',
            'bassam': 'grand-bassam',
            'grand bassam': 'grand-bassam',
            'gbassam': 'grand-bassam',
            'lahou': 'grand-lahou',
            'grand lahou': 'grand-lahou',
            'sassandra': 'sassandra',
            'bondoukou': 'bondoukou',
            'bondou': 'bondoukou',
            'séguéla': 'seguela',
            'seguela': 'seguela',
            'odienné': 'odienne',
            'odienne': 'odienne',
            
            # TIAPOUM (CIRCONSCRIPTION COMPOSÉE)
            # ✅ FIX: Simplifier l'alias pour matching SQL
            'tiapoum': 'tiapoum',  # ✅ Simple match
            'tiapum': 'tiapoum',   # ✅ Typo vers forme correcte
            'tiapom': 'tiapoum',
            'tyapoum': 'tiapoum',
            'noe': 'noe',
            'noé': 'noe',
            'nouamou': 'nouamou',
            
            # LAKOTA
            'lakota': 'lakota',
            'LAKOTA': 'lakota',
        }
    
    def _build_region_aliases(self) -> Dict[str, str]:
        """
        ✅ NOUVEAU : Aliases spécifiques pour les RÉGIONS
        
        Séparé des localités pour éviter confusion
        """
        return {
            # RÉGIONS OFFICIELLES
            'lagunes': 'lagunes',  # ✅ FIX: Maintenant cherche vraiment LAGUNES
            'la me': 'la me',
            'lame': 'la me',
            'agneby-tiassa': 'agneby-tiassa',
            'agneby': 'agneby-tiassa',
            'tiassa': 'agneby-tiassa',
            'bagoue': 'bagoue',
            'comoe': 'comoe',
            'comoé': 'comoe',
            'savanes': 'savanes',
            'zanzan': 'zanzan',
            'montagnes': 'montagnes',
            'bas-sassandra': 'bas-sassandra',
            'sassandra': 'bas-sassandra',
            'goh-djiboua': 'goh-djiboua',
            'goh': 'goh-djiboua',
            'djiboua': 'goh-djiboua',
            'lacs': 'lacs',
            'woroba': 'woroba',
            'denguele': 'denguele',
            'denguélé': 'denguele',
            'belier': 'belier',
            'bélier': 'belier',
            'gbeke': 'gbeke',
            'hambol': 'hambol',
            'tchologo': 'tchologo',
            'poro': 'poro',
            'cavally': 'cavally',
            'guemon': 'guemon',
            'tonkpi': 'tonkpi',
            'haut-sassandra': 'haut-sassandra',
            'marahoue': 'marahoue',
            'iffou': 'iffou',
            'moronou': 'moronou',
            'nzi': 'nzi',
            'indenie-djuablin': 'indenie-djuablin',
            'gontougo': 'gontougo',
            'bounkani': 'bounkani',
            'kabadougou': 'kabadougou',
            'bafing': 'bafing',
            'folon': 'folon',
            'autonome d\'abidjan': 'autonome d\'abidjan',
            'abidjan': 'autonome d\'abidjan',
            'yamoussoukro': 'autonome de yamoussoukro',
        }
    
    def _build_party_aliases(self) -> Dict[str, str]:
        """Dictionnaire d'aliases pour partis politiques"""
        return {
            # RHDP variations
            'rhdp': 'rhdp',
            'r.h.d.p': 'rhdp',
            'r.h.d.p.': 'rhdp',
            'r h d p': 'rhdp',
            'rassemblement des houphouétistes': 'rhdp',
            
            # PDCI variations
            'pdci': 'pdci-rda',
            'p.d.c.i': 'pdci-rda',
            'pdci rda': 'pdci-rda',
            'rda': 'pdci-rda',
            
            # FPI variations
            'fpi': 'fpi',
            'f.p.i': 'fpi',
            'front populaire': 'fpi',
            
            # UDPCI variations
            'udpci': 'udpci',
            'u.d.p.c.i': 'udpci',
            
            # Indépendants
            'ind': 'independant',
            'indep': 'independant',
            'indépendant': 'independant',
            'independant': 'independant',
        }
    
    def _normalize_query(self, query: str, entity_type: str) -> str:
        """
        Normalise la requête en appliquant les aliases
        
        ✅ CORRIGÉ : Utilise le bon dictionnaire selon entity_type
        """
        
        query_clean = query.lower().strip()
        query_clean = self._remove_accents(query_clean)
        
        # ✅ FIX : Appliquer le BON dictionnaire
        if entity_type == 'regions':
            # Pour régions : utiliser dictionnaire de régions
            region_aliases = self._build_region_aliases()
            if query_clean in region_aliases:
                normalized = region_aliases[query_clean]
                print(f"   🔄 Alias région: '{query}' → '{normalized}'")
                return normalized
        
        elif entity_type == 'circonscriptions':
            # Pour circonscriptions : utiliser dictionnaire de localités
            if query_clean in self.locality_aliases:
                normalized = self.locality_aliases[query_clean]
                print(f"   🔄 Alias localité: '{query}' → '{normalized}'")
                return normalized
        
        elif entity_type == 'partis':
            # Pour partis : utiliser dictionnaire de partis
            if query_clean in self.party_aliases:
                normalized = self.party_aliases[query_clean]
                print(f"   🔄 Alias parti: '{query}' → '{normalized}'")
                return normalized
        
        # Si pas d'alias, retourner query normalisée
        return query_clean
    
    def _remove_accents(self, text: str) -> str:
        """Retire les accents"""
        import unicodedata
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    def _initialize(self):
        """Initialise les index"""
        print("🔧 Initialisation RAG Indexer...")
        
        # Charger données pour difflib
        self._load_difflib_data()
        
        # Initialiser ChromaDB si disponible
        if self.use_chromadb:
            self._init_chromadb()
        
        print("✅ RAG Indexer initialisé")
    
    def _load_difflib_data(self):
        """Charge les données pour difflib"""
        
        # Circonscriptions
        circ_query = """
        SELECT DISTINCT
            circonscription_num,
            circonscription_name,
            region_normalise
        FROM election_results
        ORDER BY circonscription_num
        """
        result = self.executor.execute(circ_query)
        if result['success']:
            self.difflib_data['circonscriptions'] = result['data'].to_dict('records')
        
        # Candidats
        cand_query = """
        SELECT DISTINCT
            candidat_normalise,
            parti_normalise,
            circonscription_name
        FROM election_results
        WHERE candidat_normalise IS NOT NULL
        ORDER BY candidat_normalise
        """
        result = self.executor.execute(cand_query)
        if result['success']:
            self.difflib_data['candidats'] = result['data'].to_dict('records')
        
        # Partis
        party_query = """
        SELECT DISTINCT
            parti_normalise,
            COUNT(*) as nb_candidats
        FROM election_results
        WHERE parti_normalise IS NOT NULL
        GROUP BY parti_normalise
        ORDER BY parti_normalise
        """
        result = self.executor.execute(party_query)
        if result['success']:
            self.difflib_data['partis'] = result['data'].to_dict('records')
        
        # ✅ FIX CRITIQUE : Régions
        region_query = """
        SELECT DISTINCT
            region_normalise,
            COUNT(DISTINCT circonscription_num) as nb_circonscriptions
        FROM election_results
        WHERE region_normalise IS NOT NULL
        GROUP BY region_normalise
        ORDER BY region_normalise
        """
        result = self.executor.execute(region_query)
        if result['success']:
            self.difflib_data['regions'] = result['data'].to_dict('records')
            print(f"   📍 {len(self.difflib_data['regions'])} régions chargées")
    
    def _init_chromadb(self):
        """Initialise ChromaDB (non utilisé actuellement)"""
        pass
    
    def find_best_match(self, query: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """
        Trouve la MEILLEURE correspondance pour une entité
        
        ✅ CORRIGÉ : Meilleure gestion des régions
        """
        
        # Cache lookup
        query_normalized = self._normalize_query(query, entity_type)
        cache_key = f"{entity_type}:{query_normalized}"
        
        if self.enable_cache and self.cache_manager:
            cached = self.cache_manager.get_cached_embedding(cache_key)
            if cached is not None:
                return cached
        
        # Recherche hybride
        results = self._hybrid_search(entity_type, query_normalized, n_results=5)
        
        # Meilleur résultat
        best = results[0] if results else None
        
        # Cache le résultat
        if self.enable_cache and self.cache_manager and best:
            self.cache_manager.cache_embedding(cache_key, best)
        
        return best
    
    def find_all_good_matches(self, query: str, entity_type: str, threshold: float = 0.75) -> List[Dict[str, Any]]:
        """
        Trouve TOUS les bons matches au-dessus du seuil
        
        ✅ CORRIGÉ : Utilise normalisation correcte
        """
        
        query_normalized = self._normalize_query(query, entity_type)
        cache_key = f"{entity_type}_all:{query_normalized}:{threshold}"
        
        if self.enable_cache and self.cache_manager:
            cached = self.cache_manager.get_cached_embedding(cache_key)
            if cached is not None:
                return cached
        
        # Recherche hybride
        all_results = self._hybrid_search(entity_type, query_normalized, n_results=10)
        
        # Filtrer
        good_matches = [r for r in all_results if r['score'] >= threshold]
        
        # Cache
        if self.enable_cache and self.cache_manager:
            self.cache_manager.cache_embedding(cache_key, good_matches)
        
        return good_matches
    
    def find_circonscription(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Trouve les circonscriptions"""
        return self._hybrid_search('circonscriptions', query, n_results)
    
    def find_candidat(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Trouve les candidats"""
        return self._hybrid_search('candidats', query, n_results)
    
    def find_parti(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Trouve les partis"""
        return self._hybrid_search('partis', query, n_results)
    
    def find_region(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Trouve les régions"""
        return self._hybrid_search('regions', query, n_results)
    
    def _hybrid_search(self, entity_type: str, query: str, n_results: int) -> List[Dict[str, Any]]:
        """Recherche hybride"""
        
        query_normalized = self._normalize_query(query, entity_type)
        
        results = []
        
        # Difflib
        difflib_results = self._find_with_difflib(entity_type, query_normalized, n_results)
        for r in difflib_results:
            r['method'] = 'difflib'
        results.extend(difflib_results)
        
        # ChromaDB (si disponible)
        if self.use_chromadb and entity_type in self.collections:
            chromadb_results = self._find_with_chromadb(entity_type, query_normalized, n_results)
            for r in chromadb_results:
                r['method'] = 'chromadb'
            results.extend(chromadb_results)
        
        # Fusion et déduplication
        seen = set()
        merged = []
        
        for r in sorted(results, key=lambda x: x['score'], reverse=True):
            key = r.get('text') or r.get('circonscription_name') or r.get('candidat_normalise') or r.get('region_normalise')
            if key not in seen:
                seen.add(key)
                merged.append(r)
                if len(merged) >= n_results:
                    break
        
        return merged
    
    def _find_with_difflib(self, entity_type: str, query: str, n_results: int) -> List[Dict]:
        """Recherche avec difflib"""
        
        data = self.difflib_data.get(entity_type, [])
        
        field_map = {
            'circonscriptions': 'circonscription_name',
            'candidats': 'candidat_normalise',
            'partis': 'parti_normalise',
            'regions': 'region_normalise'  # ✅ FIX
        }
        
        field = field_map.get(entity_type)
        if not field:
            return []
        
        results = []
        
        for item in data:
            text = str(item.get(field, ''))
            
            text_normalized = self._remove_accents(text.lower())
            query_normalized = self._remove_accents(query.lower())
            
            score = SequenceMatcher(None, query_normalized, text_normalized).ratio()
            
            if score >= 0.4:
                results.append({
                    **item,
                    'text': text,
                    'score': round(score, 3)
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:n_results]
    
    def _find_with_chromadb(self, entity_type: str, query: str, n_results: int) -> List[Dict]:
        """Recherche avec ChromaDB (non utilisé)"""
        return []
    
    def clear_cache(self):
        """Vide le cache"""
        if self.cache_manager:
            stats = self.cache_manager.clear_embeddings_cache()
            print(f"🗑️ Cache vidé : {stats} embeddings supprimés")
    
    def get_cache_stats(self) -> dict:
        """Stats du cache"""
        if self.cache_manager:
            return self.cache_manager.get_cache_stats()
        return {}


def main():
    """Test du RAG corrigé"""
    
    print("="*70)
    print("🧪 TEST RAG HYBRID CORRIGÉ - Recherche régions")
    print("="*70)
    
    indexer = RAGIndexerHybrid(enable_cache=True)
    
    test_cases = [
        # ✅ TEST CRITIQUE : Régions
        ("Lagunes", "regions"),  # → Doit trouver LAGUNES
        ("Bagoue", "regions"),
        ("Agneby", "regions"),
        ("La Me", "regions"),
        
        # Circonscriptions
        ("Korogo", "circonscriptions"),
        ("Yop", "circonscriptions"),
        ("Tiapum", "circonscriptions"),
    ]
    
    for query, entity_type in test_cases:
        print(f"\n❓ Recherche: '{query}' (type: {entity_type})")
        print("-"*70)
        
        best = indexer.find_best_match(query, entity_type)
        
        if best:
            text = best.get('text') or best.get('region_normalise') or best.get('circonscription_name', 'N/A')
            score = best.get('score', 0)
            method = best.get('method', 'unknown')
            
            print(f"✅ Résultat: {text}")
            print(f"   Score: {score:.2f}")
            print(f"   Méthode: {method}")
            
            if entity_type == 'regions':
                nb_circ = best.get('nb_circonscriptions', '?')
                print(f"   Circonscriptions: {nb_circ}")
        else:
            print("❌ Aucun résultat")


if __name__ == "__main__":
    main()