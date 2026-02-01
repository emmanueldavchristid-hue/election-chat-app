"""
Disambiguator - Détecte et résout les ambiguïtés d'entités
Level 3 : Clarification + Disambiguation + Multi-step
✅ FIXED: Ne demande pas de disambiguation pour les requêtes agrégées
"""
from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.rag_indexer_hybrid import RAGIndexerHybrid


class Disambiguator:
    """Gère la désambiguation des entités ambiguës"""
    
    def __init__(self):
        self.indexer = RAGIndexerHybrid()
        
        # Mapping entity types
        self.entity_patterns = {
            'circonscription': ['circonscription', 'circ', 'commune', 'localité', 'ville'],
            'region': ['région', 'region', 'province'],
            'candidat': ['candidat', 'député', 'personne', 'élu'],
            'parti': ['parti', 'formation', 'coalition', 'groupe']
        }
    
    def _is_aggregate_query(self, question: str) -> bool:
        """
        ✅ NOUVELLE FONCTION: Détecte si la question demande une liste/agrégation
        plutôt qu'un élément spécifique
        
        Examples:
            "liste des candidats de X" → True (pas de disambiguation)
            "tous les candidats de X" → True (pas de disambiguation)
            "histogramme des candidats de X" → True (pas de disambiguation)
            "qui a gagné à X" → False (disambiguation si ambigu)
        """
        
        q_lower = question.lower()
        
        # ✅ Patterns qui indiquent une requête agrégée (TOUS les résultats)
        aggregate_patterns = [
            # Listes/pluriels
            r'\bliste\s+des?\b',
            r'\btous\s+les?\b',
            r'\btoutes\s+les?\b',
            r'\bensemble\s+des?\b',
            r'\bcandidats?\s+(?:de|à|dans)\b',  # "candidats de X"
            r'\brésultats?\s+(?:de|à|dans)\b',  # "résultats à X"
            r'\bpartis?\s+(?:de|à|dans)\b',
            
            # Graphiques/visualisations (toujours agrégés)
            r'\b(?:histogramme|graphique|diagramme|chart|courbe|camembert)\b',
            r'\b(?:fait|fais|crée|génère)\s+un\b',
            r'\bvisualisation\b',
            r'\baffiche\s+.*\s+de\b',
            
            # Agrégations/classements
            r'\btop\s+\d+\b',
            r'\bclassement\b',
            r'\bmeilleurs?\b',
            r'\bpires?\b',
            
            # Questions de comptage (pluriel)
            r'\bcombien\s+de\s+\w+s\b',  # "combien de sièges"
            r'\bnombre\s+de\b',
        ]
        
        import re
        for pattern in aggregate_patterns:
            if re.search(pattern, q_lower):
                print(f"   ✅ Requête agrégée détectée: '{pattern}'")
                return True
        
        # ✅ Patterns qui indiquent une requête spécifique (UN résultat)
        specific_patterns = [
            r'\bqui\s+a\s+gagn[éeè]\b',  # "qui a gagné"
            r'\ble\s+gagnant\b',
            r'\ble\s+vainqueur\b',
            r'\brésultat\s+du\s+candidat\b',  # "résultat du candidat X" (singulier)
        ]
        
        for pattern in specific_patterns:
            if re.search(pattern, q_lower):
                print(f"   ⚠️ Requête spécifique détectée: '{pattern}'")
                return False
        
        # Par défaut: considérer comme non-agrégée (prudent)
        return False
    
    def detect_ambiguity(self, question: str) -> Dict[str, Any]:
        """
        Détecte si la question contient une entité ambiguë
        
        ✅ MODIFICATION: Ne signale pas d'ambiguïté pour les requêtes agrégées
        
        Returns:
            {
                'is_ambiguous': bool,
                'entity_type': str | None,
                'query': str | None,
                'matches': List[Dict] | None,
                'clarification_needed': bool
            }
        """
        
        # ✅ NOUVEAU: Vérifier d'abord si c'est une requête agrégée
        if self._is_aggregate_query(question):
            print(f"   🔍 Requête agrégée → Pas de disambiguation nécessaire")
            return {
                'is_ambiguous': False,
                'clarification_needed': False,
                'reason': 'aggregate_query'
            }
        
        q_lower = question.lower()
        
        # Extraire entités potentielles (noms propres ou mots clés)
        import re
        
        # Patterns pour extraction entité
        patterns = [
            r'(?:à|dans|de|pour)\s+([A-ZÀ-Ü][a-zà-ü\-]+(?:\s+[A-ZÀ-Ü][a-zà-ü\-]+)*)',  # "à Tiapoum"
            r'\b([A-ZÀ-Ü][a-zà-ü\-]{3,})\b',  # Mots capitalisés
        ]
        
        entities_found = []
        for pattern in patterns:
            matches = re.findall(pattern, question)
            entities_found.extend(matches)
        
        if not entities_found:
            return {
                'is_ambiguous': False,
                'clarification_needed': False
            }
        
        # Déterminer le type d'entité selon le contexte
        entity_type = self._infer_entity_type(q_lower)
        
        # Chercher chaque entité
        for entity in set(entities_found):  # Dédupliquer
            
            # Normaliser l'entité avec les aliases AVANT la recherche
            entity_normalized = self.indexer._normalize_query(entity, entity_type)
            
            print(f"   🔍 Disambiguator: '{entity}' → '{entity_normalized}'")
            
            # Chercher tous les bons matches avec l'entité normalisée
            matches = self.indexer.find_all_good_matches(
                entity_normalized,
                entity_type,
                threshold=0.70  # Seuil plus bas pour capturer ambiguïtés
            )
            
            # Si aucun match trouvé avec seuil 0.70, essayer avec seuil plus bas
            if not matches:
                print(f"   🔍 Aucun match à 0.70, essai avec 0.50...")
                matches = self.indexer.find_all_good_matches(
                    entity_normalized,
                    entity_type,
                    threshold=0.50
                )
            
            # ✅ MODIFICATION: Pour candidats, vérifier si vraiment ambigu
            # Si c'est une question de liste, pas besoin de disambiguïté même si plusieurs matches
            if entity_type == 'candidats':
                # Si la question mentionne "candidats" au pluriel, c'est une liste
                if 'candidats' in q_lower or 'liste' in q_lower:
                    print(f"   ✅ Question sur liste de candidats → Pas de disambiguation")
                    return {
                        'is_ambiguous': False,
                        'clarification_needed': False,
                        'reason': 'candidate_list_query'
                    }
            
            # Si 2+ matches avec scores similaires → AMBIGUÏTÉ
            if len(matches) >= 2:
                # Vérifier si scores proches (écart < 0.15)
                top_score = matches[0]['score']
                similar_matches = [m for m in matches if (top_score - m['score']) < 0.15]
                
                if len(similar_matches) >= 2:
                    return {
                        'is_ambiguous': True,
                        'entity_type': entity_type,
                        'query': entity,  # Garder l'entité originale pour affichage
                        'matches': similar_matches[:5],  # Top 5 max
                        'clarification_needed': True
                    }
            
            # Si 1 seul match trouvé avec bon score, retourner suggestion
            elif len(matches) == 1 and matches[0]['score'] >= 0.60:
                # On a trouvé UNE correspondance claire
                print(f"   ✅ Match unique trouvé: {matches[0].get('text', 'N/A')} (score: {matches[0]['score']:.2f})")
        
        return {
            'is_ambiguous': False,
            'clarification_needed': False
        }
    
    def _infer_entity_type(self, question_lower: str) -> str:
        """Infère le type d'entité selon le contexte de la question"""
        
        # Circonscription est le plus fréquent
        for entity_type, keywords in self.entity_patterns.items():
            if any(kw in question_lower for kw in keywords):
                return entity_type + 's'  # Ajouter 's' pour match avec RAG
        
        # Par défaut : circonscription
        return 'circonscriptions'
    
    def generate_clarification_question(self, ambiguity_info: Dict) -> str:
        """
        Génère une question de clarification pour l'utilisateur
        
        Args:
            ambiguity_info: Résultat de detect_ambiguity()
        
        Returns:
            Message formaté avec options
        """
        
        entity_type = ambiguity_info['entity_type']
        query = ambiguity_info['query']
        matches = ambiguity_info['matches']
        
        # Titre
        message = f"🤔 **Précision nécessaire : '{query}'**\n\n"
        message += f"J'ai trouvé **{len(matches)} {entity_type}** correspondant(es) :\n\n"
        
        # Liste des options
        for i, match in enumerate(matches, 1):
            
            if entity_type == 'circonscriptions':
                circ_name = match.get('circonscription_name', match.get('text', ''))
                circ_num = match.get('circonscription_num', '?')
                region = match.get('region_normalise', 'Région inconnue')
                score = match.get('score', 0)
                
                message += f"**{i}.** {circ_name} (Circonscription #{circ_num}, {region})\n"
            
            elif entity_type == 'candidats':
                candidat = match.get('candidat_normalise', match.get('text', ''))
                parti = match.get('parti_normalise', 'Indépendant')
                
                message += f"**{i}.** {candidat} ({parti})\n"
            
            elif entity_type == 'partis':
                parti = match.get('parti_normalise', match.get('text', ''))
                nb_cand = match.get('nb_candidats', '?')
                
                message += f"**{i}.** {parti} ({nb_cand} candidats)\n"
            
            elif entity_type == 'regions':
                region = match.get('region_normalise', match.get('text', ''))
                nb_circ = match.get('nb_circonscriptions', '?')
                
                message += f"**{i}.** {region} ({nb_circ} circonscriptions)\n"
        
        message += "\n💡 **Répondez avec le numéro de votre choix (1, 2, 3...)**"
        
        return message
    
    def resolve_choice(self, choice_input: str, ambiguity_info: Dict) -> Optional[Dict]:
        """
        Résout le choix de l'utilisateur
        
        Args:
            choice_input: "1", "2", "le premier", etc.
            ambiguity_info: Info d'ambiguïté stockée
        
        Returns:
            Le match sélectionné ou None si invalide
        """
        
        matches = ambiguity_info['matches']
        
        # Parser le choix
        choice_lower = choice_input.lower().strip()
        
        # Détecter numéro
        import re
        number_match = re.search(r'\d+', choice_lower)
        
        if number_match:
            choice_num = int(number_match.group())
            
            if 1 <= choice_num <= len(matches):
                return matches[choice_num - 1]
        
        # Détecter "premier", "deuxième"
        ordinal_map = {
            'premier': 1, 'première': 1, '1er': 1, '1ere': 1, '1ère': 1,
            'deuxième': 2, 'second': 2, '2eme': 2, '2ème': 2,
            'troisième': 3, '3eme': 3, '3ème': 3,
        }
        
        for word, num in ordinal_map.items():
            if word in choice_lower:
                if 1 <= num <= len(matches):
                    return matches[num - 1]
        
        return None


def main():
    """Test du Disambiguator avec détection requêtes agrégées"""
    
    print("="*70)
    print("🧪 TEST DISAMBIGUATOR - Avec détection agrégées")
    print("="*70)
    
    disambiguator = Disambiguator()
    
    test_questions = [
        # ✅ REQUÊTES AGRÉGÉES (NE DOIVENT PAS déclencher disambiguation)
        "Fait un histogramme des candidats de Tiassalé",
        "Liste des candidats de Cocody",
        "Tous les candidats de Yopougon",
        "Affiche les résultats de Bouaké",
        "Top 10 des candidats",
        
        # ❌ REQUÊTES SPÉCIFIQUES (DOIVENT déclencher disambiguation si ambigu)
        "Qui a gagné à Cocody ?",
        "Le gagnant de Tiassalé",
        "Résultat du candidat Kouassi",
        
        # ✅ Tests avec aliases
        "Qui a gagné à Tiapum ?",
        "Qui a gagné à Korogo ?",
    ]
    
    for q in test_questions:
        print(f"\n❓ Question: {q}")
        print("-"*70)
        
        result = disambiguator.detect_ambiguity(q)
        
        if result['is_ambiguous']:
            print("⚠️ AMBIGUÏTÉ DÉTECTÉE !")
            print(f"   Type: {result['entity_type']}")
            print(f"   Query: {result['query']}")
            print(f"   Matches: {len(result['matches'])}")
            
            clarification = disambiguator.generate_clarification_question(result)
            print("\n" + clarification)
            
        else:
            reason = result.get('reason', 'N/A')
            print(f"✅ Pas d'ambiguïté (raison: {reason})")


if __name__ == "__main__":
    main()