"""
Query Validator - Version Production Corrigée
Validateur SQL pour l'application d'analyse électorale
100% compatible avec l'application Streamlit/Gradio

Protège contre:
- Injections SQL
- Commandes destructives (DROP, DELETE, UPDATE, INSERT, ALTER, CREATE)
- Accès non autorisés
- Requêtes coûteuses
"""

import re
import logging
from typing import Dict, List, Set, Optional

logger = logging.getLogger(__name__)


class QueryValidator:
    """
    Validateur SQL production-ready
    Retourne 'sanitized_sql' au lieu de 'query'
    """
    
    # ========================================================================
    # CONFIGURATION DE SÉCURITÉ
    # ========================================================================
    
    # Commandes destructives absolument interdites
    DESTRUCTIVE_KEYWORDS = {
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT',
        'UPDATE', 'REPLACE', 'GRANT', 'REVOKE', 'PRAGMA', 'ATTACH',
        'DETACH', 'VACUUM', 'REINDEX', 'EXEC', 'EXECUTE'
    }
    
    # Tables autorisées (schéma d'élections)
    ALLOWED_TABLES = {
        'election_results', 'elections',
        'vw_winners', 'vw_party_results', 'vw_turnout',
        'vw_region_results', 'vw_close_races'
    }
    
    # Limites de sécurité
    MAX_RESULT_SIZE = 10000
    DEFAULT_LIMIT = 1000
    MAX_QUERY_LENGTH = 5000
    
    def __init__(self, max_limit: int = None):
        """
        Initialise le validateur
        
        Args:
            max_limit: Limite max de résultats (défaut: 1000)
        """
        self.max_limit = max_limit or self.DEFAULT_LIMIT
        self.last_error = None
        self.warnings = []
    
    # ========================================================================
    # MÉTHODE PRINCIPALE - validate()
    # ========================================================================
    
    def validate(self, query: str) -> Dict:
        """
        Valide une requête SQL
        
        Returns:
            Dict avec:
                - valid (bool): True si valide
                - sanitized_sql (str): Requête nettoyée
                - errors (List[str]): Liste d'erreurs
                - warnings (List[str]): Avertissements
        """
        self.last_error = None
        self.warnings = []
        errors = []
        
        try:
            # ----------------------------------------------------------------
            # ÉTAPE 0: Validation de base
            # ----------------------------------------------------------------
            if not query or not isinstance(query, str):
                return self._error('Requête vide ou invalide')
            
            query = query.strip()
            
            if len(query) > self.MAX_QUERY_LENGTH:
                return self._error(f'Requête trop longue (max: {self.MAX_QUERY_LENGTH})')
            
            # ----------------------------------------------------------------
            # ÉTAPE 1: Bloquer commandes destructives
            # ----------------------------------------------------------------
            destructive_error = self._check_destructive(query)
            if destructive_error:
                return self._error(destructive_error)
            
            # ----------------------------------------------------------------
            # ÉTAPE 2: Doit être un SELECT
            # ----------------------------------------------------------------
            select_error = self._check_is_select(query)
            if select_error:
                return self._error(select_error)
            
            # ----------------------------------------------------------------
            # ÉTAPE 3: Vérifier syntaxe (FORM au lieu de FROM, etc.)
            # ----------------------------------------------------------------
            syntax_error = self._check_syntax_errors(query)
            if syntax_error:
                return self._error(syntax_error)
            
            # ----------------------------------------------------------------
            # ÉTAPE 4: Vérifier tables autorisées
            # ----------------------------------------------------------------
            table_error = self._check_allowed_tables(query)
            if table_error:
                return self._error(table_error)
            
            # ----------------------------------------------------------------
            # ÉTAPE 5: Bloquer commentaires et multi-statements
            # ----------------------------------------------------------------
            comment_error = self._check_no_comments_or_multi(query)
            if comment_error:
                return self._error(comment_error)
            
            # ----------------------------------------------------------------
            # ÉTAPE 6: Ajouter/vérifier LIMIT
            # ----------------------------------------------------------------
            query, limit_error = self._ensure_limit(query)
            if limit_error:
                return self._error(limit_error)
            
            # ----------------------------------------------------------------
            # SUCCÈS
            # ----------------------------------------------------------------
            return {
                'valid': True,
                'sanitized_sql': query.rstrip(';'),  # ✅ CORRIGÉ: 'sanitized_sql' au lieu de 'query'
                'errors': [],
                'warnings': self.warnings
            }
            
        except Exception as e:
            logger.error(f"Erreur validation: {str(e)}")
            return self._error(f'Erreur de validation: {str(e)}')
    
    # ========================================================================
    # CHECKS INDIVIDUELS
    # ========================================================================
    
    def _check_destructive(self, query: str) -> Optional[str]:
        """
        Bloque toutes les commandes destructives
        Retourne le message d'erreur ou None
        """
        query_upper = query.upper()
        
        for keyword in self.DESTRUCTIVE_KEYWORDS:
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, query_upper):
                return f'Commande interdite: {keyword} (opération destructive)'
        
        return None
    
    def _check_is_select(self, query: str) -> Optional[str]:
        """
        Vérifie que c'est un SELECT
        Retourne le message d'erreur ou None
        """
        query_upper = query.strip().upper()
        
        # Autoriser WITH ... SELECT (CTE)
        if query_upper.startswith('WITH'):
            if 'SELECT' not in query_upper:
                return 'Requête WITH doit contenir SELECT'
            return None
        
        if not query_upper.startswith('SELECT'):
            return 'Seules les requêtes SELECT sont autorisées'
        
        return None
    
    def _check_syntax_errors(self, query: str) -> Optional[str]:
        """
        Détecte les erreurs de syntaxe communes
        Retourne le message d'erreur ou None
        """
        query_upper = query.upper()
        
        # Erreurs communes
        if re.search(r'\bFORM\b', query_upper):
            return 'Erreur syntaxe: utilisez FROM au lieu de FORM'
        
        if re.search(r'\bSELCT\b', query_upper):
            return 'Erreur syntaxe: utilisez SELECT au lieu de SELCT'
        
        if re.search(r'\bWHERE\s+WHERE\b', query_upper):
            return 'Erreur syntaxe: WHERE dupliqué'
        
        # WHERE incomplet
        if re.search(r'\bWHERE\s*;', query_upper):
            return 'Erreur syntaxe: WHERE incomplet'
        
        # FROM incomplet
        if re.search(r'\bFROM\s*;', query_upper):
            return 'Erreur syntaxe: FROM incomplet'
        
        return None
    
    def _check_allowed_tables(self, query: str) -> Optional[str]:
        """
        Vérifie que seules les tables autorisées sont utilisées
        Retourne le message d'erreur ou None
        """
        try:
            # Extraction des tables
            from_matches = re.findall(r'FROM\s+(\w+)', query, re.IGNORECASE)
            join_matches = re.findall(r'JOIN\s+(\w+)', query, re.IGNORECASE)
            
            all_tables = set(from_matches + join_matches)
            
            for table in all_tables:
                if table.lower() not in [t.lower() for t in self.ALLOWED_TABLES]:
                    return f'Table non autorisée: {table}'
            
            return None
        except Exception as e:
            # En cas d'erreur d'extraction, on laisse passer
            logger.warning(f"Erreur extraction tables: {e}")
            return None
    
    def _check_no_comments_or_multi(self, query: str) -> Optional[str]:
        """
        Bloque commentaires SQL et multi-statements
        Retourne le message d'erreur ou None
        """
        # Commentaires SQL
        if '--' in query:
            return 'Commentaires SQL (--) interdits'
        
        if '/*' in query or '*/' in query:
            return 'Commentaires SQL (/* */) interdits'
        
        # Multi-statements
        semicolon_count = query.count(';')
        
        if semicolon_count > 1:
            return 'Multi-statements interdits (plusieurs ;)'
        
        if semicolon_count == 1 and not query.rstrip().endswith(';'):
            return 'Point-virgule uniquement en fin de requête'
        
        return None
    
    def _ensure_limit(self, query: str) -> tuple[str, Optional[str]]:
        """
        Ajoute LIMIT si absent, vérifie si trop grand
        Retourne (query_modifiée, message_erreur)
        """
        query_upper = query.upper()
        
        # Chercher LIMIT existant
        limit_match = re.search(r'\bLIMIT\s+(\d+)', query_upper)
        
        if limit_match:
            # LIMIT existe
            limit_value = int(limit_match.group(1))
            
            if limit_value > self.MAX_RESULT_SIZE:
                return (query, f'LIMIT trop élevé: {limit_value} (max: {self.MAX_RESULT_SIZE})')
            
            if limit_value > self.max_limit:
                self.warnings.append(f'LIMIT {limit_value} est élevé (recommandé: {self.max_limit})')
            
            return (query, None)
        else:
            # LIMIT absent, l'ajouter
            sanitized = query.rstrip(';') + f' LIMIT {self.max_limit}'
            self.warnings.append(f'LIMIT {self.max_limit} ajouté automatiquement')
            return (sanitized, None)
    
    def _error(self, msg: str) -> Dict:
        """Construit un résultat d'erreur"""
        self.last_error = msg
        return {
            'valid': False,
            'sanitized_sql': None,  # ✅ CORRIGÉ: 'sanitized_sql' au lieu de 'query'
            'errors': [msg],
            'warnings': self.warnings
        }
    
    # ========================================================================
    # MÉTHODES UTILITAIRES
    # ========================================================================
    
    def sanitize_prompt(self, prompt: str, max_length: int = 500) -> str:
        """
        Nettoie un prompt utilisateur
        """
        if not prompt:
            return ""
        
        # Supprimer caractères dangereux
        sanitized = re.sub(r'[;\\]', '', prompt)
        
        # Supprimer commandes SQL dans le prompt
        for keyword in self.DESTRUCTIVE_KEYWORDS:
            sanitized = re.sub(
                r'\b' + keyword + r'\b',
                '',
                sanitized,
                flags=re.IGNORECASE
            )
        
        # Limiter la longueur
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()


# ============================================================================
# INSTANCE GLOBALE
# ============================================================================

_default_validator = None


def get_validator() -> QueryValidator:
    """Retourne l'instance globale du validateur"""
    global _default_validator
    if _default_validator is None:
        _default_validator = QueryValidator()
    return _default_validator


def validate_query(query: str) -> Dict:
    """
    Fonction utilitaire pour valider une requête
    """
    return get_validator().validate(query)


# ============================================================================
# TESTS RAPIDES
# ============================================================================

def main():
    """Tests rapides pour vérification"""
    validator = QueryValidator()
    
    print("="*70)
    print("🧪 TESTS QUERY VALIDATOR")
    print("="*70)
    
    test_cases = [
        # ✅ Requêtes valides
        ("SELECT * FROM election_results", True, "Requête basique"),
        ("SELECT COUNT(*) FROM vw_winners", True, "Avec COUNT"),
        ("SELECT candidat FROM election_results WHERE elu = TRUE", True, "Avec WHERE"),
        
        # ❌ Commandes destructives
        ("DROP TABLE election_results", False, "DROP interdit"),
        ("DELETE FROM election_results", False, "DELETE interdit"),
        ("UPDATE election_results SET elu = TRUE", False, "UPDATE interdit"),
        ("INSERT INTO election_results VALUES (1, 'test')", False, "INSERT interdit"),
        
        # ❌ Injections
        ("SELECT * FROM election_results; DROP TABLE users;", False, "Injection multi-statement"),
        ("SELECT * FROM election_results -- comment", False, "Commentaire SQL"),
        
        # ❌ Syntaxe incorrecte
        ("SELECT * FORM election_results", False, "FORM au lieu de FROM"),
        
        # ❌ Tables interdites
        ("SELECT * FROM unknown_table", False, "Table non autorisée"),
    ]
    
    passed = 0
    failed = 0
    
    for sql, should_pass, description in test_cases:
        print(f"\n📝 Test: {description}")
        print(f"   SQL: {sql[:60]}{'...' if len(sql) > 60 else ''}")
        
        result = validator.validate(sql)
        success = result['valid'] == should_pass
        
        if success:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        print(f"   {status}")
        
        if not result['valid']:
            if 'errors' in result and result['errors']:
                print(f"   Erreur: {result['errors'][0]}")
        else:
            print(f"   SQL nettoyé: {result['sanitized_sql'][:60]}...")
        
        if result.get('warnings'):
            print(f"   Warnings: {', '.join(result['warnings'])}")
    
    print("\n" + "="*70)
    print(f"📊 Résultats: {passed} réussis, {failed} échoués sur {len(test_cases)} tests")
    
    if failed == 0:
        print("🎉 Tous les tests passent !")
    else:
        print(f"⚠️ {failed} test(s) ont échoué")
    
    print("="*70)


if __name__ == "__main__":
    main()