"""
SQL Generator - VERSION HYBRIDE FINALE OPTIMALE
✅ FIX BUG #1: Typos (Tiapum → Tiapoum) avec dict locality_corrections
✅ FIX BUG #2: Abidjan (région) → Disambiguation via intent_classifier
✅ FIX BUG #3: Requêtes complexes (indépendants vs RHDP) - Exemples SQL
✅ FIX BUG #4: Hors-sujet détecté AVANT génération SQL
✅ FIX BUG #5: "candidats de X" → Force circonscription_name (règle géographique)
✅ Colonnes statistiques avec MAX()
✅ ILIKE au lieu de REGEXP
✅ source_page TOUJOURS présent
✅ Validation SQL basique
"""
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import json
from dotenv import load_dotenv
import re
import unicodedata

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.llm_client import LLMClient

# Import RAG
try:
    from src.agent.rag_indexer_hybrid import RAGIndexerHybrid
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("⚠️ RAG Indexer non disponible. SQL basique utilisé.")

load_dotenv()


class SQLGenerator:
    """Generate SQL queries from natural language using LLM + RAG."""
    
    def __init__(self):
        """Initialize SQL generator with LLM client and RAG."""
        self.client = LLMClient()
        
        # Initialiser RAG si disponible
        if RAG_AVAILABLE:
            try:
                self.rag = RAGIndexerHybrid()
                self.rag_enabled = True
                print("✅ RAG Indexer chargé et prêt")
            except Exception as e:
                print(f"⚠️ RAG Indexer erreur: {e}")
                self.rag_enabled = False
        else:
            self.rag_enabled = False
        
        # ✅ DICTIONNAIRE CORRECTIONS TYPOS (FIX BUG #1)
        self.locality_corrections = {
            # Typos fréquents
            'tiapum': 'tiapoum',
            'tiassale': 'tiassalé',
            'korogo': 'korhogo',
            'bouake': 'bouaké',
            
            # Circonscriptions composées
            'noe': 'noe, nouamou et tiapoum',
            'nouamou': 'noe, nouamou et tiapoum',
            'tiapoum': 'noe, nouamou et tiapoum',
            
            # Abréviations communes
            'yop': 'yopougon',
            'adjame': 'adjamé',
            'attecoube': 'attécoubé',
            'coco': 'cocody',
            'cocode': 'cocody',
            'treich': 'treichville',
            'marko': 'marcory',
            'marco': 'marcory',
        }
        
        # ✅ MOTS-CLÉS HORS-SUJET (FIX BUG #4)
        self.off_topic_keywords = [
            'capitale', 'france', 'paris', 'météo', 'weather', 'température',
            'sport', 'football', 'match', 'basket', 'tennis',
            'recette', 'cuisine', 'restaurant', 'plat',
            'film', 'série', 'netflix', 'cinéma', 'acteur',
            'macron', 'biden', 'trump', 'poutine',
            'crypto', 'bitcoin', 'bourse', 'actions',
        ]
        
        self.electoral_keywords = [
            'élection', 'election', 'vote', 'votant', 'candidat', 'parti',
            'siège', 'siege', 'circonscription', 'rhdp', 'pdci', 'fpi',
            'gagné', 'elu', 'élu', 'résultat', 'voix', 'bulletin',
            'participation', 'taux', 'inscrits', 'suffrages',
        ]
        
        # ✅ RÉGIONS CONNUES (pour détecter ambiguïté Abidjan)
        self.known_regions = {
            'abidjan', 'gbeke', 'gontougo', 'cavally', 'bafing', 
            'agneby-tiassa', 'tonkpi', 'moronou', 'nzi', 'hambol',
        }
        
        # Database schema documentation
        self.schema_doc = """
DATABASE SCHEMA:

Table: election_results
Columns:
- id, region, region_normalise, circonscription_num, circonscription_name
- nb_bureaux, inscrits, votants, taux_participation
- bulletins_nuls, suffrages_exprimes, bulletins_blancs_nombre, bulletins_blancs_pourcentage
- parti, parti_normalise, candidat, candidat_normalise
- voix, pourcentage_voix, elu (BOOLEAN)
- source_page, table_id, row_id

🔴 CRITICAL: COLONNES DE STATISTIQUES
Ces colonnes sont IDENTIQUES pour tous les candidats d'une circonscription:
- inscrits, votants, taux_participation, bulletins_nuls, bulletins_blancs_nombre, suffrages_exprimes, nb_bureaux

⚠️ RÈGLES:
1. Pour UNE circonscription: Utiliser MAX() pour obtenir UNE valeur
   SELECT MAX(bulletins_nuls), MAX(inscrits), MAX(source_page) FROM ...
   
2. Pour agrégations régionales: AVG() ou SUM(DISTINCT ...)
   SELECT ROUND(AVG(taux_participation), 2), SUM(DISTINCT inscrits) FROM ...

3. TOUJOURS inclure source_page ou pages_sources

EXEMPLES CORRECTS:

Q: "Combien de bulletins nuls à Adjamé ?"
SQL:
SELECT MAX(bulletins_nuls) as bulletins_nuls, MAX(source_page) as source_page
FROM election_results
WHERE circonscription_name ILIKE '%adjamé%'

Q: "Qui a gagné à Cocody ?"
SQL:
SELECT candidat_normalise, parti_normalise, voix, pourcentage_voix, source_page
FROM election_results
WHERE circonscription_name ILIKE '%cocody%' AND elu = TRUE
LIMIT 10

Q: "Y a-t-il des circonscriptions où un indépendant a battu le RHDP ?"
SQL:
SELECT 
    e1.circonscription_name,
    e1.candidat_normalise as candidat_independant,
    e1.voix as voix_independant,
    COALESCE(e2.voix, 0) as voix_rhdp,
    e1.source_page
FROM election_results e1
LEFT JOIN election_results e2 
    ON e1.circonscription_num = e2.circonscription_num 
    AND e2.parti_normalise = 'RHDP'
WHERE e1.parti_normalise = 'INDEPENDANT' 
    AND e1.elu = TRUE
    AND (e2.voix IS NULL OR e1.voix > e2.voix)
LIMIT 100

📄 CITATION REQUIREMENTS:
- TOUJOURS inclure source_page ou pages_sources
- Agrégations: STRING_AGG(DISTINCT CAST(source_page AS VARCHAR), ', ') as pages_sources
- Simples: SELECT ..., source_page FROM ...

🔴 CRITICAL: GÉOGRAPHIE
- Villes/Circonscriptions → circonscription_name ILIKE '%nom%'
- Régions → region_normalise = 'NOM_REGION'
- "candidats de X" → X est TOUJOURS une ville → circonscription_name

🔴 CRITICAL: GROUP BY
- Si COUNT/SUM/AVG/MAX/MIN ET sélection autres colonnes → GROUP BY obligatoire
- OU utiliser STRING_AGG() / ANY_VALUE() pour colonnes non agrégées
"""
    
    def generate_sql(self, question: str) -> Dict[str, any]:
        """
        Generate SQL from natural language question.
        
        Returns:
            Dict with 'sql', 'explanation', 'intent', 'success', 'off_topic', 'needs_disambiguation'
        """
        
        # ✅ ÉTAPE 0: Détection hors-sujet AVANT génération SQL (FIX BUG #4)
        if self._is_off_topic(question):
            return {
                'sql': '',
                'explanation': 'Question hors-sujet',
                'intent': 'off_topic',
                'success': False,
                'error': 'Cette question ne concerne pas les élections 2025 de Côte d\'Ivoire.',
                'off_topic': True
            }
        
        # ✅ ÉTAPE 0.5: Détection ambiguïté RÉGIONS (FIX BUG #2)
        # Ex: "Qui a gagné à Abidjan ?" → Abidjan = région avec 12+ circonscriptions
        disambiguation_info = self._detect_region_ambiguity(question)
        if disambiguation_info['needs_disambiguation']:
            return {
                'sql': '',
                'explanation': 'Disambiguation needed',
                'intent': 'disambiguation',
                'success': False,
                'needs_disambiguation': True,
                'disambiguation_info': disambiguation_info,
                'error': 'Veuillez préciser la circonscription.'
            }
        
        # ✅ ÉTAPE 1: Normaliser question (typos) (FIX BUG #1)
        normalized_question, corrections = self._normalize_question(question)
        
        # ✅ ÉTAPE 2: Enrichissement RAG
        enriched_question = normalized_question
        rag_context = ""
        
        if self.rag_enabled:
            enriched_question, rag_context = self._enrich_with_rag(normalized_question)
        
        # ✅ ÉTAPE 3: Générer SQL avec contexte enrichi
        system_prompt = f"""You are a SQL expert for Ivory Coast election results (2025).

{self.schema_doc}

{rag_context}

STRICT RULES:
1. ONLY SELECT queries (no INSERT/UPDATE/DELETE/DROP)
2. ALWAYS add LIMIT (max 100)
3. ALWAYS include source_page for citations
4. Use ILIKE for text matching (case-insensitive, accent-insensitive)
5. For statistics (inscrits, votants, bulletins_nuls): use MAX()
6. Return ONLY SQL, no JSON, no markdown, no explanation

CORRECTIONS APPLIED:
{corrections if corrections else "None"}

🔴 CRITICAL: "CANDIDATS DE X" QUERIES
When user asks for "candidats de [lieu]", ALWAYS use circonscription_name:
- ✅ CORRECT: WHERE circonscription_name ILIKE '%{'{lieu}'}%'
- ❌ WRONG: WHERE region_normalise = '{'{LIEU}'}'

Return ONLY valid DuckDB SQL or "OFF_TOPIC" if question is not about elections."""

        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": enriched_question}],
                max_tokens=800,
                temperature=0,
                system=system_prompt
            )
            
            content = response['content'][0]['text'].strip()
            
            # Vérifier si LLM a détecté hors-sujet
            if 'OFF_TOPIC' in content.upper() or 'HORS' in content.upper():
                return {
                    'sql': '',
                    'explanation': 'Question hors-sujet détectée par LLM',
                    'intent': 'off_topic',
                    'success': False,
                    'error': 'Cette question ne concerne pas les élections.',
                    'off_topic': True
                }
            
            # Extraire SQL
            sql = self._extract_sql_from_response(content)
            
            if not sql:
                return {
                    'sql': '',
                    'explanation': 'Failed to extract SQL',
                    'intent': 'error',
                    'success': False,
                    'error': 'Impossible de générer une requête SQL valide. Reformulez votre question.'
                }
            
            # ✅ Post-processing: Règles géographiques (FIX BUG #5)
            sql = self._fix_geographic_issues(sql, normalized_question)
            
            # ✅ Post-processing: Corrections générales
            sql = self._fix_common_issues(sql)
            
            # Validation basique
            if not self._validate_sql_basic(sql):
                return {
                    'sql': '',
                    'explanation': 'Invalid SQL',
                    'intent': 'error',
                    'success': False,
                    'error': 'Requête SQL invalide générée. Reformulez votre question.'
                }
            
            intent = self._detect_intent(normalized_question, sql)
            
            return {
                'sql': sql,
                'explanation': 'SQL query generated successfully',
                'intent': intent,
                'success': True,
                'rag_used': self.rag_enabled,
                'corrections_applied': corrections,
                'tokens_input': response.get('usage', {}).get('input_tokens', 200),
                'tokens_output': response.get('usage', {}).get('output_tokens', 100)
            }
            
        except Exception as e:
            return {
                'sql': '',
                'explanation': f'Failed to generate SQL: {e}',
                'intent': 'error',
                'success': False,
                'error': f'Erreur lors de la génération SQL: {str(e)}'
            }
    
    def _is_off_topic(self, question: str) -> bool:
        """Détecte si question hors-sujet (FIX BUG #4)."""
        q_lower = question.lower()
        
        has_off_topic = any(keyword in q_lower for keyword in self.off_topic_keywords)
        has_electoral = any(keyword in q_lower for keyword in self.electoral_keywords)
        
        # Hors-sujet si: mot off-topic présent ET PAS de mot électoral
        return has_off_topic and not has_electoral
    
    def _detect_region_ambiguity(self, question: str) -> Dict[str, any]:
        """
        ✅ NOUVEAU: Détecte si question mentionne une RÉGION (FIX BUG #2)
        
        Ex: "Qui a gagné à Abidjan ?" → Abidjan = région avec 12 circonscriptions
        → Nécessite disambiguation
        
        Returns:
            {
                'needs_disambiguation': bool,
                'region_detected': str | None,
                'message': str | None
            }
        """
        
        q_lower = question.lower()
        
        # Patterns de questions géographiques
        geo_patterns = [
            r'(?:qui\s+a\s+gagn[ée]|gagnant|vainqueur|résultat)\s+(?:à|dans|de)\s+([a-zàâäéèêëïîôùûüÿç\-\']+)',
            r'(?:candidats?|résultats?)\s+(?:de|à|dans)\s+([a-zàâäéèêëïîôùûüÿç\-\']+)',
        ]
        
        for pattern in geo_patterns:
            match = re.search(pattern, q_lower)
            if match:
                location = match.group(1).strip()
                location_clean = self._remove_accents(location)
                
                # Vérifier si c'est une RÉGION connue
                if location_clean in self.known_regions:
                    return {
                        'needs_disambiguation': True,
                        'region_detected': location,
                        'message': f"'{location.title()}' est une région avec plusieurs circonscriptions. Veuillez préciser la circonscription."
                    }
        
        return {
            'needs_disambiguation': False,
            'region_detected': None,
            'message': None
        }
    
    def _normalize_question(self, question: str) -> Tuple[str, str]:
        """Normalise question avec corrections typos (FIX BUG #1)."""
        
        normalized = question
        corrections = []
        
        # Extraire mots potentiels
        words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿç]{3,}\b', question.lower())
        
        for word in words:
            word_clean = self._remove_accents(word)
            
            # Vérifier si correction connue
            if word_clean in self.locality_corrections:
                corrected = self.locality_corrections[word_clean]
                normalized = re.sub(
                    rf'\b{word}\b', 
                    corrected, 
                    normalized, 
                    flags=re.IGNORECASE
                )
                corrections.append(f"'{word}' → '{corrected}'")
        
        corrections_str = " | ".join(corrections) if corrections else ""
        return normalized, corrections_str
    
    def _fix_geographic_issues(self, sql: str, question: str) -> str:
        """
        ✅ FIX BUG #5: Force circonscription_name pour "candidats de X"
        
        RÈGLE: "candidats de X" → X est TOUJOURS une ville/circonscription
        → Utiliser circonscription_name ILIKE, JAMAIS region_normalise
        """
        
        q_lower = question.lower()
        
        # Patterns indiquant recherche de candidats dans un lieu
        candidate_location_patterns = [
            r'candidats?\s+(?:de|à|dans)\s+([a-zàâäéèêëïîôùûüÿç\-\']+)',
            r'résultats?\s+(?:de|à|dans)\s+([a-zàâäéèêëïîôùûüÿç\-\']+)',
            r'(?:qui\s+a\s+gagn[ée])\s+(?:à|dans)\s+([a-zàâäéèêëïîôùûüÿç\-\']+)',
            r'(?:liste|tous)\s+.*\s+(?:de|à|dans)\s+([a-zàâäéèêëïîôùûüÿç\-\']+)',
            r'histogramme\s+.*\s+(?:de|à|dans)\s+([a-zàâäéèêëïîôùûüÿç\-\']+)',
        ]
        
        for pattern in candidate_location_patterns:
            match = re.search(pattern, q_lower)
            if match:
                location = match.group(1)
                location_clean = self._remove_accents(location.lower())
                
                print(f"   🔍 Détecté: requête candidats dans '{location}'")
                print(f"   🔄 Normalisé: '{location_clean}'")
                
                # CAS 1: Si SQL utilise region_normalise → CORRIGER
                if 'region_normalise' in sql.lower():
                    print(f"   ⚠️  SQL utilise region_normalise (incorrect!)")
                    sql = re.sub(
                        r"region_normalise\s*=\s*'[^']+'",
                        f"circonscription_name ILIKE '%{location_clean}%'",
                        sql,
                        flags=re.IGNORECASE
                    )
                    print(f"   ✅ Corrigé: circonscription_name ILIKE '%{location_clean}%'")
                
                # CAS 2: Si PAS de WHERE circonscription_name, l'AJOUTER
                elif 'circonscription_name' not in sql.lower():
                    print(f"   ⚠️  SQL ne filtre pas sur circonscription_name!")
                    
                    if 'WHERE' in sql.upper():
                        sql = re.sub(
                            r'(WHERE\s+)',
                            rf'\1circonscription_name ILIKE \'%{location_clean}%\' AND ',
                            sql,
                            count=1,
                            flags=re.IGNORECASE
                        )
                    else:
                        insert_pos = sql.upper().find('ORDER BY')
                        if insert_pos == -1:
                            insert_pos = sql.upper().find('LIMIT')
                        if insert_pos == -1:
                            insert_pos = len(sql)
                        
                        sql = sql[:insert_pos] + f" WHERE circonscription_name ILIKE '%{location_clean}%' " + sql[insert_pos:]
                    
                    print(f"   ✅ Ajouté: WHERE circonscription_name ILIKE '%{location_clean}%'")
                
                # CAS 3: Si SQL utilise REGEXP_MATCHES → SIMPLIFIER avec ILIKE
                elif 'REGEXP_MATCHES' in sql:
                    print(f"   ⚠️  SQL utilise REGEXP (peut échouer avec accents)")
                    sql = re.sub(
                        r"REGEXP_MATCHES\(circonscription_name,\s*'[^']+',\s*'i'\)",
                        f"circonscription_name ILIKE '%{location_clean}%'",
                        sql,
                        flags=re.IGNORECASE
                    )
                    print(f"   ✅ Corrigé: circonscription_name ILIKE '%{location_clean}%'")
                
                # CAS 4: Si SQL utilise = exact → REMPLACER par ILIKE
                elif re.search(r"circonscription_name\s*=\s*'[^']+'", sql, re.IGNORECASE):
                    print(f"   ⚠️  SQL utilise = exact (trop strict)")
                    sql = re.sub(
                        r"circonscription_name\s*=\s*'[^']+'",
                        f"circonscription_name ILIKE '%{location_clean}%'",
                        sql,
                        flags=re.IGNORECASE
                    )
                    print(f"   ✅ Corrigé: circonscription_name ILIKE '%{location_clean}%'")
                
                break
        
        return sql
    
    def _fix_common_issues(self, sql: str) -> str:
        """Corrections générales SQL."""
        
        # Assurer LIMIT
        if 'LIMIT' not in sql.upper():
            sql += ' LIMIT 100'
        
        # Nettoyer espaces
        sql = ' '.join(sql.split())
        
        return sql
    
    def _validate_sql_basic(self, sql: str) -> bool:
        """Validation basique SQL."""
        sql_upper = sql.upper()
        
        if not sql_upper.strip().startswith('SELECT'):
            return False
        if 'LIMIT' not in sql_upper:
            return False
        
        forbidden = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'TRUNCATE']
        if any(word in sql_upper for word in forbidden):
            return False
        
        return True
    
    def _extract_sql_from_response(self, response_text: str) -> str:
        """Extrait SQL depuis réponse LLM."""
        
        # Markdown
        if '```sql' in response_text.lower():
            match = re.search(r'```sql\s*(SELECT.*?)```', response_text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        if '```' in response_text:
            match = re.search(r'```\s*(SELECT.*?)```', response_text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # JSON
        if '"sql"' in response_text:
            match = re.search(r'"sql"\s*:\s*"(SELECT.*?)"', response_text, re.DOTALL | re.IGNORECASE)
            if match:
                sql = match.group(1)
                sql = sql.replace('\\"', '"').replace('\\n', '\n')
                return sql.rstrip('",}').strip()
        
        # SQL pur
        match = re.search(r'(SELECT\s+.*?(?:LIMIT\s+\d+|;|\Z))', response_text, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
            return sql.rstrip(';').rstrip('",}').strip()
        
        return ""
    
    def _detect_intent(self, question: str, sql: str) -> str:
        """Détecte intent de la question."""
        q_lower = question.lower()
        sql_upper = sql.upper()
        
        if any(w in q_lower for w in ['histogramme', 'graphique', 'diagramme', 'chart', 'camembert', 'courbe']):
            return 'chart'
        
        if 'ORDER BY' in sql_upper and any(w in q_lower for w in ['top', 'meilleur', 'classement']):
            return 'ranking'
        
        if any(func in sql_upper for func in ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN(', 'GROUP BY']):
            return 'aggregation'
        
        return 'lookup'
    
    def _enrich_with_rag(self, question: str) -> Tuple[str, str]:
        """Enrichit question avec RAG."""
        if not self.rag_enabled:
            return question, ""
        
        enrichments = []
        rag_context = "\nRAG CONTEXT:\n"
        
        words = re.findall(r'\b[A-ZÀ-Ÿa-zà-ÿ]{3,}\b', question)
        
        for word in words:
            if word.lower() in ['qui', 'quoi', 'comment', 'combien', 'quel', 'quelle']:
                continue
            
            # Chercher circonscription
            circ_match = self.rag.find_best_match(word, 'circonscriptions')
            if circ_match and circ_match['score'] > 0.6:
                full_name = circ_match.get('circonscription_name', '')
                enrichments.append(f'"{word}" → "{full_name}"')
                rag_context += f"- '{word}' → '{full_name}'\n"
                continue
            
            # Chercher parti
            parti_match = self.rag.find_best_match(word, 'partis')
            if parti_match and parti_match['score'] > 0.7:
                parti_name = parti_match.get('parti_normalise', '')
                enrichments.append(f'"{word}" → "{parti_name}"')
                rag_context += f"- '{word}' → parti '{parti_name}'\n"
        
        enriched = question
        if enrichments:
            enriched += "\n\n[Entités: " + ", ".join(enrichments) + "]"
        
        return enriched, rag_context if enrichments else ""
    
    def _remove_accents(self, text: str) -> str:
        """Retire les accents d'un texte."""
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')


def main():
    """Test du générateur SQL FINAL."""
    generator = SQLGenerator()
    
    print("="*70)
    print("🧪 TEST SQL GENERATOR - VERSION HYBRIDE FINALE")
    print("="*70)
    
    test_questions = [
        ("Qui a gagné à Tiapum ?", "Typo fix"),  # FIX #1
        ("Qui a gagné à Abidjan ?", "Région disambiguation"),  # FIX #2
        ("Y a-t-il des circonscriptions où un indépendant a battu le RHDP ?", "Requête complexe"),  # FIX #3
        ("Quelle est la capitale de la France ?", "Hors-sujet"),  # FIX #4
        ("Fait un histogramme des candidats de Tiassalé", "Candidats de X"),  # FIX #5
        ("Combien de bulletins nuls à Adjamé ?", "Colonnes stat"),
    ]
    
    for i, (question, test_name) in enumerate(test_questions, 1):
        print(f"\n{'='*70}")
        print(f"❓ Test {i}: {test_name}")
        print(f"   Question: {question}")
        print("-"*70)
        
        result = generator.generate_sql(question)
        
        if result.get('off_topic'):
            print(f"🚫 HORS-SUJET: {result.get('error')}")
        elif result.get('needs_disambiguation'):
            print(f"🤔 DISAMBIGUATION: {result['disambiguation_info']['message']}")
        elif result['success']:
            print(f"✅ Intent: {result['intent']}")
            print(f"🔎 SQL:\n{result['sql']}")
            if result.get('corrections_applied'):
                print(f"🔧 Corrections: {result['corrections_applied']}")
        else:
            print(f"❌ Error: {result.get('error')}")


if __name__ == "__main__":
    main()