"""
Intent Classifier - Version CORRIGÉE
✅ FIX: Détecte le TYPE EXACT de graphique (pie/bar/line)
✅ FIX: Retourne chart_type dans le résultat
"""
from typing import Dict, Any
import re


class IntentClassifier:
    """Classifie l'intention rapidement avec des règles"""
    
    def __init__(self):
        # Pas besoin de LLM !
        pass
    
    def classify(self, question: str) -> Dict[str, Any]:
        """
        Classifie la question en catégories d'intention.
        
        Returns:
            {
                'intent': 'sql_query' | 'fraud_analysis' | 'conversation' | 'off_topic' | 'chart',
                'confidence': 0.0-1.0,
                'requires_sql': bool,
                'requires_analysis': bool,
                'chart_type': 'pie' | 'bar' | 'line' | None,  # ✅ NOUVEAU
                'explanation': str
            }
        """
        
        q_lower = question.lower()
        
        # ✅ 0. CHART/GRAPHIQUE (PRIORITÉ HAUTE - avant conversation)
        chart_type_detected = self._detect_chart_type(q_lower)
        
        if chart_type_detected:
            return {
                'intent': 'chart',
                'confidence': 0.95,
                'requires_sql': True,
                'requires_analysis': False,
                'chart_type': chart_type_detected,  # ✅ NOUVEAU
                'explanation': f'Demande de graphique {chart_type_detected} détectée'
            }
        
        # 1. CONVERSATION (salutations, remerciements)
        conversation_keywords = [
            'bonjour', 'salut', 'hello', 'hi', 'bonsoir', 'bonne nuit',
            'merci', 'thank', 'cool', 'super', 'génial', 'parfait',
            'comment tu', 'comment fonctionn', 'aide', 'help', 'peux-tu',
            'que peux', 'qui es-tu', 'présente-toi'
        ]
        
        if any(keyword in q_lower for keyword in conversation_keywords):
            # EXCEPTION: Si "merci" + autre chose substantielle, c'est pas juste conversation
            if 'merci' in q_lower and len(q_lower.split()) > 3:
                pass  # Continue vers SQL
            else:
                return {
                    'intent': 'conversation',
                    'confidence': 0.95,
                    'requires_sql': False,
                    'requires_analysis': False,
                    'chart_type': None,
                    'explanation': 'Salutation ou question générale'
                }
        
        # 2. FRAUD ANALYSIS (fraudes, anomalies)
        fraud_keywords = [
            'fraude', 'fraud', 'triche', 'manipulation', 'suspect',
            'anomalie', 'incohérence', 'bizarre', 'étrange', 'anormal',
            '100%', 'cent pourcent', 'trop haute', 'trop basse'
        ]
        
        if any(keyword in q_lower for keyword in fraud_keywords):
            return {
                'intent': 'fraud_analysis',
                'confidence': 0.9,
                'requires_sql': False,
                'requires_analysis': True,
                'chart_type': None,
                'explanation': 'Demande d\'analyse de fraude'
            }
        
        # 3. OFF-TOPIC (hors sujet)
        offtopic_keywords = [
            'météo', 'temps qu\'il fait', 'weather',
            'match', 'foot', 'sport', 'basket',
            'recette', 'cuisine', 'restaurant',
            'film', 'série', 'musique',
            'crypto', 'bitcoin', 'bourse'
        ]
        
        if any(keyword in q_lower for keyword in offtopic_keywords):
            return {
                'intent': 'off_topic',
                'confidence': 0.95,
                'requires_sql': False,
                'requires_analysis': False,
                'chart_type': None,
                'explanation': 'Question hors sujet'
            }
        
        # 4. SQL QUERY (par défaut)
        # Indices de requête SQL
        sql_indicators = [
            'combien', 'qui', 'quel', 'quelle', 'quels', 'quelles',
            'liste', 'montre', 'affiche', 'donne',
            'top', 'classement', 'meilleur', 'plus',
            'résultat', 'siège', 'voix', 'vote', 'candidat', 'parti',
            'circonscription', 'région', 'participation', 'taux'
        ]
        
        has_sql_indicator = any(keyword in q_lower for keyword in sql_indicators)
        
        return {
            'intent': 'sql_query',
            'confidence': 0.9 if has_sql_indicator else 0.7,
            'requires_sql': True,
            'requires_analysis': False,
            'chart_type': None,
            'explanation': 'Question factuelle nécessitant une requête SQL'
        }
    
    def _detect_chart_type(self, q_lower: str) -> str:
        """
        ✅ NOUVELLE MÉTHODE : Détecte le TYPE EXACT de graphique demandé
        
        Returns:
            'pie' | 'bar' | 'line' | None
        """
        
        # 1️⃣ PIE CHART (camembert) - PRIORITÉ HAUTE
        pie_keywords = [
            'camembert', 'circulaire', 'pie', 'tarte', 'secteurs',
            'répartition', 'pourcentages', 'parts'
        ]
        
        pie_patterns = [
            r'\b(pie\s+chart|diagramme\s+circulaire|graphique\s+circulaire)\b',
            r'\bcamembert\b',
            r'\b(tarte|secteurs)\b'
        ]
        
        # Vérifier patterns spécifiques PIE
        for pattern in pie_patterns:
            if re.search(pattern, q_lower):
                return 'pie'
        
        # Vérifier mots-clés PIE
        if any(kw in q_lower for kw in pie_keywords):
            # Exception: si "bar" ou "histogramme" aussi présent, c'est ambigu
            if not any(word in q_lower for word in ['bar', 'barre', 'histogramme', 'histogram']):
                return 'pie'
        
        # 2️⃣ LINE CHART (courbe) - PRIORITÉ MOYENNE
        line_keywords = [
            'courbe', 'ligne', 'évolution', 'line', 'tendance', 'progression'
        ]
        
        line_patterns = [
            r'\b(line\s+chart|courbe|ligne)\b',
            r'\b(évolution|tendance|progression)\b'
        ]
        
        # Vérifier patterns LINE
        for pattern in line_patterns:
            if re.search(pattern, q_lower):
                return 'line'
        
        # Vérifier mots-clés LINE
        if any(kw in q_lower for kw in line_keywords):
            return 'line'
        
        # 3️⃣ BAR CHART (histogramme/barres) - PRIORITÉ BASSE (défaut)
        bar_keywords = [
            'histogramme', 'histogram', 'barre', 'barres', 'bar',
            'graphique', 'diagramme', 'chart', 'visualisation', 'visualise',
            'plot', 'montre graphique', 'affiche graphique', 'trace',
            'dessine', 'représente graphiquement'
        ]
        
        bar_patterns = [
            r'\b(fait|fais|crée|génère|produis)\s+(un|une|le|la)?\s*(graphique|histogramme|diagramme|chart)\b',
            r'\b(bar\s+chart|histogramme|diagramme\s+en\s+barres)\b',
            r'\b(graphique|diagramme|chart)\b'
        ]
        
        # Vérifier patterns BAR
        for pattern in bar_patterns:
            if re.search(pattern, q_lower):
                return 'bar'
        
        # Vérifier mots-clés BAR
        if any(kw in q_lower for kw in bar_keywords):
            return 'bar'
        
        # Aucun graphique détecté
        return None


def main():
    """Test du classificateur corrigé"""
    
    classifier = IntentClassifier()
    
    test_questions = [
        # PIE CHARTS (doit retourner chart_type='pie')
        ("Fait un diagramme circulaire des candidats de Cocody", 'pie'),
        ("Fais un camembert des sièges par parti", 'pie'),
        ("pie chart participation", 'pie'),
        ("Répartition en pourcentages des voix", 'pie'),
        
        # BAR CHARTS (doit retourner chart_type='bar')
        ("fait un histogramme des candidats", 'bar'),
        ("Fais un graphique en barres", 'bar'),
        ("bar chart des sièges", 'bar'),
        ("Montre-moi un graphique", 'bar'),
        
        # LINE CHARTS (doit retourner chart_type='line')
        ("Courbe de la participation par région", 'line'),
        ("line chart évolution", 'line'),
        ("Tendance des voix", 'line'),
        
        # SQL (pas de graphique)
        ("Combien de sièges a gagné le RHDP ?", None),
        ("Top 10 des candidats", None),
    ]
    
    print("="*80)
    print("🧪 TEST INTENT CLASSIFIER CORRIGÉ")
    print("="*80)
    print("\n✅ Détection précise du TYPE de graphique (pie/bar/line)\n")
    
    errors = 0
    success = 0
    
    for question, expected_chart_type in test_questions:
        print(f"\n❓ Question: {question}")
        print(f"   🎯 Attendu: chart_type={expected_chart_type}")
        print("-"*80)
        
        result = classifier.classify(question)
        
        emoji = {
            'chart': '📊',
            'sql_query': '🔍',
            'fraud_analysis': '🚨',
            'conversation': '💬',
            'off_topic': '🚫'
        }.get(result['intent'], '❓')
        
        print(f"{emoji} Intent: {result['intent']}")
        print(f"📊 Chart Type: {result.get('chart_type', 'N/A')}")
        print(f"🎚️  Confidence: {result['confidence']}")
        print(f"💡 Explanation: {result['explanation']}")
        
        # Validation
        detected_type = result.get('chart_type')
        
        if expected_chart_type is None:
            # Pas de graphique attendu
            if detected_type is None:
                print("✅ CORRECT: Aucun graphique détecté")
                success += 1
            else:
                print(f"❌ ERREUR: Graphique détecté alors que non attendu (got: {detected_type})")
                errors += 1
        else:
            # Graphique attendu
            if detected_type == expected_chart_type:
                print(f"✅ CORRECT: Type {detected_type} détecté")
                success += 1
            else:
                print(f"❌ ERREUR: Attendu '{expected_chart_type}', obtenu '{detected_type}'")
                errors += 1
    
    print("\n" + "="*80)
    print(f"📊 RÉSULTATS: {success}/{len(test_questions)} tests réussis")
    if errors == 0:
        print("🎉 TOUS LES TESTS PASSENT !")
    else:
        print(f"⚠️  {errors} erreur(s) détectée(s)")
    print("="*80)


if __name__ == "__main__":
    main()