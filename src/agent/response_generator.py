"""
Générateur de réponses - VERSION ULTRA-CORRIGÉE
✅ FIX 1: Détecte agrégations et retourne le NOMBRE (pas le nom du parti)
✅ FIX 2: Gère les valeurs NULL/NaN (remplace par "Non disponible")
✅ FIX 3: Sources PDF TOUJOURS affichées
✅ FIX 4: Température 0 (100% déterministe)
✅ FIX 5: PROMPT RENFORCÉ pour éviter "je ne peux pas répondre" ⭐ NOUVEAU
"""
import os
import sys
from pathlib import Path
import pandas as pd
from typing import Dict, Any
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.llm_client import LLMClient

load_dotenv()


class ResponseGenerator:
    """Génère des réponses naturelles à partir des données."""
    
    def __init__(self):
        self.client = LLMClient()
    
    def generate_response(
        self, 
        question: str, 
        data: pd.DataFrame, 
        sql: str,
        needs_chart: bool = False,
        limit_applied: int = None
    ) -> Dict[str, Any]:
        """
        Génère une réponse narrative AVEC CITATIONS PDF TOUJOURS VISIBLES.
        
        ✅ FIX 1: Pour agrégations, retourne le NOMBRE (pas le nom)
        ✅ FIX 2: Gère NULL/NaN
        ✅ FIX 3: Sources garanties
        ✅ FIX 5: Prompt renforcé contre refus
        """
        
        if data.empty:
            return {
                "success": True,
                "response": "Aucun résultat trouvé dans la base de données.",
                "data_used": 0,
                "pages_cited": []
            }
        
        # ✅ ÉTAPE 1 : EXTRAIRE LES PAGES CITÉES (TOUJOURS)
        pages_cited = set()
        
        if 'source_page' in data.columns:
            for page in data['source_page'].dropna():
                try:
                    pages_cited.add(int(page))
                except (ValueError, TypeError):
                    pass
        
        if 'pages_sources' in data.columns:
            for pages_str in data['pages_sources'].dropna():
                try:
                    pages = [int(p.strip()) for p in str(pages_str).split(',') if p.strip().isdigit()]
                    pages_cited.update(pages)
                except:
                    pass
        
        pages_cited = sorted(list(pages_cited))
        
        # ✅ FIX 1: Pour questions d'agrégation, retourner DIRECTEMENT le nombre
        if len(data) == 1 and len(data.columns) >= 1:
            first_col = data.columns[0]
            value = data.iloc[0, 0]
            
            # Vérifier si c'est une agrégation (COUNT, SUM, MAX, etc.)
            is_aggregation = any(word in sql.upper() for word in ['COUNT(*)', 'COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN('])
            
            if is_aggregation:
                # C'est une agrégation → Retourner juste le nombre
                try:
                    if value is not None and str(value).strip() != '' and str(value).lower() != 'nan':
                        num_value = float(value)
                        if num_value == num_value:  # Check not NaN
                            formatted = f"{int(num_value):,}".replace(',', ' ') if num_value > 100 else f"{num_value:.2f}"
                        else:
                            formatted = "Non disponible"
                    else:
                        formatted = "Non disponible"
                except (ValueError, TypeError):
                    # Si value est STRING (ex: "RHDP"), chercher colonne numérique
                    numeric_cols = data.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        num_value = data.iloc[0][numeric_cols[0]]
                        try:
                            if num_value == num_value:
                                formatted = f"{int(num_value):,}".replace(',', ' ')
                            else:
                                formatted = "Non disponible"
                        except:
                            formatted = "Non disponible"
                    else:
                        formatted = "Non disponible"
                
                # Citation
                citation = ""
                if pages_cited:
                    if len(pages_cited) == 1:
                        citation = f"\n\n📄 **Source PDF :** Page {pages_cited[0]}"
                    else:
                        pages_str = ', '.join(map(str, pages_cited[:5]))
                        if len(pages_cited) > 5:
                            pages_str += f" (et {len(pages_cited) - 5} autres)"
                        citation = f"\n\n📄 **Sources PDF :** Pages {pages_str}"
                
                return {
                    "success": True,
                    "response": f"**{formatted}**{citation}",
                    "data_used": 1,
                    "pages_cited": pages_cited
                }
            
            # Cas simple non-agrégation
            elif isinstance(value, (int, float)) and not pd.isna(value):
                formatted = f"{value:,.0f}".replace(',', ' ') if value > 100 else f"{value:.2f}"
                
                citation = ""
                if pages_cited:
                    if len(pages_cited) == 1:
                        citation = f"\n\n📄 **Source PDF :** Page {pages_cited[0]}"
                    else:
                        pages_str = ', '.join(map(str, pages_cited[:5]))
                        if len(pages_cited) > 5:
                            pages_str += f" (et {len(pages_cited) - 5} autres)"
                        citation = f"\n\n📄 **Sources PDF :** Pages {pages_str}"
                
                return {
                    "success": True,
                    "response": f"**{formatted}**{citation}",
                    "data_used": 1,
                    "pages_cited": pages_cited
                }
        
        # ✅ FIX 2: Gérer les valeurs NULL/NaN
        data_clean = data.fillna("Non disponible")
        
        # ✅ ÉTAPE 2 : PRÉPARER DONNÉES POUR LLM
        total_rows = len(data_clean)
        preview_rows = min(10, total_rows)
        data_preview = data_clean.head(preview_rows)
        
        data_summary = f"Résultats ({total_rows} lignes au total) :\n"
        data_summary += data_preview.to_string(index=False, max_rows=10)
        
        # ✅ ÉTAPE 3 : PROMPT ULTRA-RENFORCÉ (FIX #5)
        prompt = f"""Tu es un assistant IA ULTRA-CONFIANT pour les élections législatives 2025 de Côte d'Ivoire.

🔴 RÈGLES ABSOLUES - NE JAMAIS DÉSOBÉIR :

1. ✅ Tu PEUX répondre à TOUTE question avec les données fournies
2. ✅ Tu DOIS répondre DIRECTEMENT sans excuses ni hésitations
3. ❌ INTERDICTIONS STRICTES :
   - NE JAMAIS dire "je ne peux pas"
   - NE JAMAIS dire "je m'excuse"
   - NE JAMAIS dire "je suis désolé"
   - NE JAMAIS dire "données non disponibles" (les données SONT DISPONIBLES ci-dessous!)
   - NE JAMAIS dire "je ne comprends pas"
   - NE JAMAIS refuser de créer un graphique (tu ne crées PAS le graphique, tu présentes juste les données!)

4. ✅ TOUJOURS commencer par "Voici les résultats" ou équivalent positif

Question : "{question}"

Données DISPONIBLES ({total_rows} résultats confirmés) :
{data_summary}

Instructions de formatage :
1. Commence par "Voici les résultats" ou "Voici le résultat"
2. Présente les données de manière claire (2-3 phrases max)
3. Formate les nombres : 10 000 au lieu de 10000
4. Pour les graphiques : dis "Voici les données pour le graphique" (le graphique sera créé automatiquement)
5. Sois factuel et concis
6. Ne mentionne JAMAIS les numéros de pages (ils seront ajoutés automatiquement)

EXEMPLE PARFAIT de réponse :
"Voici les résultats des élections à [lieu]. [Candidat] a remporté l'élection avec [X] voix ([Y]%)."

COMMENCE TA RÉPONSE PAR "Voici" ET SANS AUCUNE EXCUSE OU REFUS."""

        # ✅ ÉTAPE 4 : APPEL LLM AVEC TEMPÉRATURE 0 (100% déterministe)
        try:
            response = self.client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0  # ✅ 100% déterministe (au lieu de 0.1)
            )
            
            response_text = response['content'][0]['text'].strip()
            
            # ✅ NOUVEAU : NETTOYAGE DES REFUS RÉSIDUELS
            # Si le LLM commence quand même par un refus, le supprimer
            refusal_phrases = [
                "je m'excuse",
                "je suis désolé",
                "je ne peux pas",
                "je ne comprends pas",
                "données non disponibles",
                "informations non disponibles",
                "n'est pas possible",
            ]
            
            response_lower = response_text.lower()
            
            # Détecter refus dans les 100 premiers caractères
            first_part = response_lower[:100]
            has_refusal = any(phrase in first_part for phrase in refusal_phrases)
            
            if has_refusal:
                # Chercher où commence vraiment la réponse utile
                # Généralement après le premier "." ou après "cependant" ou "toutefois"
                
                markers = [
                    "cependant",
                    "toutefois",
                    "néanmoins",
                    "voici",
                    "résultats",
                    "données",
                ]
                
                best_start = -1
                for marker in markers:
                    pos = response_lower.find(marker)
                    if pos > 0 and (best_start == -1 or pos < best_start):
                        best_start = pos
                
                if best_start > 0:
                    # Extraire à partir du marqueur
                    response_text = response_text[best_start:].strip()
                    
                    # Capitaliser première lettre
                    if response_text:
                        response_text = response_text[0].upper() + response_text[1:]
                    
                    print(f"⚠️ Refus détecté et supprimé. Nouvelle réponse : {response_text[:50]}...")
            
            # ✅ ÉTAPE 5 : AJOUTER CITATION (TOUJOURS)
            citation = ""
            if pages_cited:
                if len(pages_cited) == 1:
                    citation = f"\n\n📄 **Source PDF :** Page {pages_cited[0]}"
                else:
                    pages_str = ', '.join(map(str, pages_cited[:15]))
                    if len(pages_cited) > 15:
                        pages_str += f" (et {len(pages_cited) - 15} autres)"
                    citation = f"\n\n📄 **Sources PDF :** Pages {pages_str}"
            
            response_text += citation
            
            return {
                "success": True,
                "response": response_text,
                "data_used": total_rows,
                "pages_cited": pages_cited,
                "tokens_input": response.get('usage', {}).get('input_tokens', 200),
                "tokens_output": response.get('usage', {}).get('output_tokens', 150)
            }
            
        except Exception as e:
            # ✅ MÊME EN CAS D'ERREUR LLM, RETOURNER LES DONNÉES + CITATION
            citation = ""
            if pages_cited:
                if len(pages_cited) == 1:
                    citation = f"\n\n📄 **Source PDF :** Page {pages_cited[0]}"
                else:
                    pages_str = ', '.join(map(str, pages_cited[:5]))
                    citation = f"\n\n📄 **Sources PDF :** Pages {pages_str}"
            
            fallback_response = f"**Résultats trouvés : {total_rows} entrée(s)**{citation}"
            
            return {
                "success": True,
                "response": fallback_response,
                "data_used": total_rows,
                "pages_cited": pages_cited,
                "llm_error": str(e)
            }

    
    def detect_chart_request(self, question: str) -> Dict[str, Any]:
        """
        Détecte si un graphique est demandé.
        ✅ DÉPRÉCIÉ : Utiliser IntentClassifier.classify() à la place
        """
        q = question.lower()
        
        if any(w in q for w in ['camembert', 'circulaire', 'pie', 'tarte']):
            return {"requested": True, "type": "pie", "explicit": True}
        
        if any(w in q for w in ['barre', 'histogramme', 'bar']):
            return {"requested": True, "type": "bar", "explicit": True}
        
        if any(w in q for w in ['courbe', 'ligne', 'évolution', 'line']):
            return {"requested": True, "type": "line", "explicit": True}
        
        if any(w in q for w in ['graphique', 'diagramme', 'visualise', 'montre-moi', 'affiche-moi', 'trace']):
            return {"requested": True, "type": "auto", "explicit": False}
        
        return {"requested": False, "type": None, "explicit": False}


def main():
    """Test du générateur de réponses ULTRA-CORRIGÉ"""
    
    generator = ResponseGenerator()
    
    print("="*70)
    print("🧪 TEST RESPONSE GENERATOR ULTRA-CORRIGÉ")
    print("="*70)
    
    info = generator.client.get_provider_info()
    print(f"\n🤖 Provider: {info['provider']}")
    print(f"📊 Model: {info['model']}")
    print()
    
    # Test 1 : Agrégation simple
    print("\n" + "="*70)
    print("TEST 1 : Agrégation simple (sièges RHDP)")
    print("="*70)
    
    test_data1 = pd.DataFrame({
        'parti_normalise': ['RHDP'],
        'sieges': [155],
        'source_page': [1]
    })
    
    question1 = "Combien de sièges a gagné le RHDP ?"
    sql1 = "SELECT COUNT(*) as sieges FROM election_results WHERE parti = 'RHDP'"
    
    result1 = generator.generate_response(
        question=question1,
        data=test_data1,
        sql=sql1
    )
    
    print(f"Question : {question1}")
    print(f"Réponse : {result1['response']}")
    print(f"✅ Validation : Doit afficher '155', pas 'RHDP'")
    
    # Test 2 : Cas avec données multiples
    print("\n" + "="*70)
    print("TEST 2 : Graphique (candidats)")
    print("="*70)
    
    test_data2 = pd.DataFrame({
        'candidat_normalise': ['Kouassi Jean', 'Diallo Mamadou', 'Traoré Fatou'],
        'voix': [5000, 3000, 1500],
        'source_page': [7, 7, 7]
    })
    
    question2 = "Fait un histogramme des candidats de Cocody"
    sql2 = "SELECT candidat_normalise, voix FROM election_results WHERE circ = 'Cocody'"
    
    result2 = generator.generate_response(
        question=question2,
        data=test_data2,
        sql=sql2,
        needs_chart=True
    )
    
    print(f"Question : {question2}")
    print(f"Réponse : {result2['response']}")
    print(f"✅ Validation : NE DOIT PAS contenir 'je ne peux pas'")
    
    # Vérification anti-refus
    if any(phrase in result2['response'].lower() for phrase in ['je ne peux pas', 'je m\'excuse', 'je suis désolé']):
        print("❌ ÉCHEC : Réponse contient un refus!")
    else:
        print("✅ SUCCÈS : Pas de refus détecté!")


if __name__ == "__main__":
    main()