"""
Fraud Analyzer - Détecte les anomalies et incohérences électorales
Analyse les données pour identifier des patterns suspects
"""
import pandas as pd
from typing import Dict, Any, List
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.query_executor import QueryExecutor
from src.utils.config import DB_PATH


class FraudAnalyzer:
    """Analyse les données électorales pour détecter des anomalies"""
    
    def __init__(self):
        self.executor = QueryExecutor(DB_PATH)
        self.executor.connect()
    
    def analyze(self, question: str) -> Dict[str, Any]:
        """
        Analyse la question et retourne les anomalies détectées.
        
        Returns:
            {
                'success': bool,
                'anomalies_found': bool,
                'analysis_type': str,
                'results': pd.DataFrame,
                'summary': str,
                'recommendations': List[str]
            }
        """
        
        q_lower = question.lower()
        
        # Déterminer le type d'analyse
        if any(word in q_lower for word in ['fraude', 'fraud', 'triche', 'manipulation']):
            return self._detect_fraud_patterns()
        
        elif any(word in q_lower for word in ['100%', 'cent pourcent', 'pourcentage', 'incohérence']):
            return self._check_percentage_inconsistencies()
        
        elif any(word in q_lower for word in ['participation', 'suspect', 'anormal', 'anomalie']):
            return self._check_turnout_anomalies()
        
        elif any(word in q_lower for word in ['voix', 'votes', 'bizarre', 'étrange']):
            return self._check_vote_anomalies()
        
        else:
            # Analyse générale
            return self._general_anomaly_scan()
    
    def _check_percentage_inconsistencies(self) -> Dict[str, Any]:
        """Vérifie les incohérences de pourcentages - AMÉLIORÉ"""
        
        # 1. Vérification classique (code existant lignes 65-105)
        sql_classic = """
        WITH circonscription_totals AS (
            SELECT 
                circonscription_num,
                circonscription_name,
                region_normalise,
                MAX(inscrits) as inscrits,
                MAX(votants) as votants,
                MAX(suffrages_exprimes) as suffrages_exprimes,
                SUM(voix) as total_voix_candidats,
                MAX(taux_participation) as taux_participation
            FROM election_results
            GROUP BY circonscription_num, circonscription_name, region_normalise
        )
        SELECT 
            circonscription_num,
            circonscription_name,
            region_normalise,
            inscrits,
            votants,
            suffrages_exprimes,
            total_voix_candidats,
            taux_participation,
            ROUND((votants * 100.0 / NULLIF(inscrits, 0)), 2) as taux_calc,
            ROUND((total_voix_candidats * 100.0 / NULLIF(suffrages_exprimes, 0)), 2) as pourcentage_voix_total,
            CASE 
                WHEN votants > inscrits THEN 'Votants > Inscrits'
                WHEN total_voix_candidats > suffrages_exprimes THEN 'Voix candidats > Suffrages exprimés'
                WHEN ABS(taux_participation - (votants * 100.0 / NULLIF(inscrits, 0))) > 1 THEN 'Taux participation incohérent'
                ELSE NULL
            END as anomalie
        FROM circonscription_totals
        WHERE 
            votants > inscrits
            OR total_voix_candidats > suffrages_exprimes
            OR ABS(taux_participation - (votants * 100.0 / NULLIF(inscrits, 0))) > 1
        ORDER BY circonscription_num
        LIMIT 100
        """
        
        result_classic = self.executor.execute(sql_classic)
        
        # 2. ✅ NOUVEAU: Vérification somme pourcentages
        pct_sum_check = self._check_percentage_sum_inconsistencies()
        
        # Combiner les résultats
        if result_classic['success']:
            data_classic = result_classic['data']
        else:
            data_classic = pd.DataFrame()
        
        total_anomalies = len(data_classic) + len(pct_sum_check['results'])
        
        if total_anomalies > 0:
            summary = f"🚨 **{total_anomalies} incohérences détectées au total**\n\n"
            
            # Résumé classique
            if len(data_classic) > 0:
                summary += f"**Incohérences classiques:** {len(data_classic)} cas\n"
                for anomaly_type in data_classic['anomalie'].unique():
                    count = len(data_classic[data_classic['anomalie'] == anomaly_type])
                    summary += f"- {anomaly_type}: {count}\n"
                summary += "\n"
            
            # Résumé somme pourcentages
            summary += pct_sum_check['summary']
        else:
            summary = "✅ Aucune incohérence détectée. Les données semblent cohérentes."
        
        return {
            'success': True,
            'anomalies_found': total_anomalies > 0,
            'analysis_type': 'percentage_check',
            'results': pct_sum_check['results'],  # Retourner surtout les incohérences de somme
            'summary': summary,
            'recommendations': [
                "Vérifier les données sources",
                "Comparer avec les procès-verbaux officiels",
                "Contacter la CEI pour clarification"
            ] if total_anomalies > 0 else []
        }
    
    def _check_turnout_anomalies(self) -> Dict[str, Any]:
        """Détecte les taux de participation anormaux"""
        
        sql = """
        WITH stats AS (
            SELECT 
                AVG(taux_participation) as avg_participation,
                STDDEV(taux_participation) as stddev_participation
            FROM (
                SELECT DISTINCT circonscription_num, taux_participation
                FROM election_results
            )
        )
        SELECT DISTINCT
            er.circonscription_num,
            er.circonscription_name,
            er.region_normalise,
            er.inscrits,
            er.votants,
            er.taux_participation,
            s.avg_participation,
            ROUND(er.taux_participation - s.avg_participation, 2) as ecart_moyenne,
            CASE
                WHEN er.taux_participation > 95 THEN 'Très haute (>95%)'
                WHEN er.taux_participation < 20 THEN 'Très basse (<20%)'
                WHEN er.taux_participation > s.avg_participation + (2 * s.stddev_participation) THEN 'Anormalement haute'
                WHEN er.taux_participation < s.avg_participation - (2 * s.stddev_participation) THEN 'Anormalement basse'
                ELSE NULL
            END as type_anomalie
        FROM election_results er
        CROSS JOIN stats s
        WHERE 
            er.taux_participation > 95
            OR er.taux_participation < 20
            OR er.taux_participation > s.avg_participation + (2 * s.stddev_participation)
            OR er.taux_participation < s.avg_participation - (2 * s.stddev_participation)
        ORDER BY er.taux_participation DESC
        LIMIT 50
        """
        
        result = self.executor.execute(sql)
        
        if not result['success']:
            return {
                'success': False,
                'anomalies_found': False,
                'analysis_type': 'turnout_anomalies',
                'results': pd.DataFrame(),
                'summary': f"Erreur: {result.get('error')}",
                'recommendations': []
            }
        
        data = result['data']
        anomalies_found = len(data) > 0
        
        if anomalies_found:
            summary = f"📊 **{len(data)} circonscriptions avec participation anormale**\n\n"
            for anomaly_type in data['type_anomalie'].unique():
                count = len(data[data['type_anomalie'] == anomaly_type])
                summary += f"- {anomaly_type}: {count} cas\n"
        else:
            summary = "✅ Aucune anomalie de participation détectée."
        
        return {
            'success': True,
            'anomalies_found': anomalies_found,
            'analysis_type': 'turnout_anomalies',
            'results': data,
            'summary': summary,
            'recommendations': [
                "Analyser les facteurs géographiques et démographiques",
                "Vérifier les conditions de vote dans ces circonscriptions"
            ] if anomalies_found else []
        }
    
    def _check_percentage_sum_inconsistencies(self) -> Dict[str, Any]:
        """
        ✅ NOUVEAU: Vérifie si SUM(pourcentage_voix) = 100% par circonscription
        """
        
        sql = """
        WITH circonscription_pct AS (
            SELECT 
                circonscription_num,
                circonscription_name,
                region_normalise,
                SUM(pourcentage_voix) as total_pct,
                COUNT(*) as nb_candidats,
                MAX(source_page) as source_page
            FROM election_results
            GROUP BY circonscription_num, circonscription_name, region_normalise
        )
        SELECT 
            circonscription_num,
            circonscription_name,
            region_normalise,
            ROUND(total_pct, 2) as total_pourcentage,
            nb_candidats,
            source_page,
            ROUND(ABS(total_pct - 100), 2) as ecart_100,
            CASE 
                WHEN total_pct > 100.5 THEN 'Somme > 100%'
                WHEN total_pct < 99.5 THEN 'Somme < 100%'
                ELSE 'OK'
            END as type_anomalie
        FROM circonscription_pct
        WHERE ABS(total_pct - 100) > 0.5
        ORDER BY ABS(total_pct - 100) DESC
        LIMIT 100
        """
        
        result = self.executor.execute(sql)
        
        if not result['success']:
            return {
                'success': False,
                'anomalies_found': False,
                'analysis_type': 'percentage_sum',
                'results': pd.DataFrame(),
                'summary': f"Erreur: {result.get('error')}",
                'recommendations': []
            }
        
        data = result['data']
        anomalies_found = len(data) > 0
        
        if anomalies_found:
            summary = f"🚨 **{len(data)} circonscriptions avec somme ≠ 100%**\n\n"
            
            # Compter par type
            sup_100 = len(data[data['type_anomalie'] == 'Somme > 100%'])
            inf_100 = len(data[data['type_anomalie'] == 'Somme < 100%'])
            
            if sup_100 > 0:
                summary += f"- Somme > 100% : {sup_100} cas\n"
            if inf_100 > 0:
                summary += f"- Somme < 100% : {inf_100} cas\n"
            
            # Top 5 pires cas
            summary += f"\n📊 Top 5 incohérences:\n"
            for idx, row in data.head(5).iterrows():
                summary += f"- {row['circonscription_name']}: {row['total_pourcentage']:.2f}% (écart: {row['ecart_100']:.2f})\n"
        else:
            summary = "✅ Toutes les circonscriptions ont des sommes cohérentes (~100%)."
        
        return {
            'success': True,
            'anomalies_found': anomalies_found,
            'analysis_type': 'percentage_sum',
            'results': data,
            'summary': summary,
            'recommendations': [
                "Vérifier les données sources",
                "Recompter manuellement",
                "Contacter la CEI"
            ] if anomalies_found else []
        }
    
    def _check_vote_anomalies(self) -> Dict[str, Any]:
        """Détecte les anomalies dans les votes"""
        
        sql = """
        SELECT 
            circonscription_num,
            circonscription_name,
            region_normalise,
            parti_normalise,
            candidat_normalise,
            voix,
            pourcentage_voix,
            elu,
            CASE
                WHEN pourcentage_voix > 90 THEN 'Victoire écrasante (>90%)'
                WHEN pourcentage_voix = 100 THEN 'Score parfait suspect'
                ELSE NULL
            END as type_anomalie
        FROM election_results
        WHERE 
            pourcentage_voix > 90
            OR (voix = 0 AND elu = TRUE)
        ORDER BY pourcentage_voix DESC
        LIMIT 50
        """
        
        result = self.executor.execute(sql)
        
        if not result['success'] or len(result['data']) == 0:
            return {
                'success': True,
                'anomalies_found': False,
                'analysis_type': 'vote_anomalies',
                'results': pd.DataFrame(),
                'summary': "✅ Aucune anomalie significative dans les votes.",
                'recommendations': []
            }
        
        data = result['data']
        
        summary = f"🔍 **{len(data)} cas de votes atypiques**\n\n"
        summary += "Scores supérieurs à 90% détectés."
        
        return {
            'success': True,
            'anomalies_found': True,
            'analysis_type': 'vote_anomalies',
            'results': data,
            'summary': summary,
            'recommendations': [
                "Vérifier la compétitivité dans ces circonscriptions",
                "Analyser le contexte politique local"
            ]
        }
    
    def _detect_fraud_patterns(self) -> Dict[str, Any]:
        """Analyse globale des patterns de fraude potentielle"""
        
        # Combine plusieurs vérifications
        percentage_check = self._check_percentage_inconsistencies()
        turnout_check = self._check_turnout_anomalies()
        vote_check = self._check_vote_anomalies()
        
        total_anomalies = (
            len(percentage_check['results']) +
            len(turnout_check['results']) +
            len(vote_check['results'])
        )
        
        summary = f"🔬 **Analyse de fraude complète**\n\n"
        summary += f"Total d'anomalies détectées: {total_anomalies}\n\n"
        summary += f"- Incohérences de pourcentages: {len(percentage_check['results'])}\n"
        summary += f"- Anomalies de participation: {len(turnout_check['results'])}\n"
        summary += f"- Votes atypiques: {len(vote_check['results'])}\n"
        
        # Combiner les résultats
        all_results = pd.concat([
            percentage_check['results'],
            turnout_check['results'],
            vote_check['results']
        ], ignore_index=True)
        
        return {
            'success': True,
            'anomalies_found': total_anomalies > 0,
            'analysis_type': 'fraud_detection',
            'results': all_results,
            'summary': summary,
            'recommendations': [
                "Audit approfondi des circonscriptions suspectes",
                "Vérification croisée avec les observateurs électoraux",
                "Analyse des procès-verbaux originaux"
            ] if total_anomalies > 0 else []
        }
    
    def _general_anomaly_scan(self) -> Dict[str, Any]:
        """Scan général des anomalies"""
        return self._detect_fraud_patterns()


def main():
    """Test du détecteur de fraude"""
    
    analyzer = FraudAnalyzer()
    
    test_questions = [
        "Y a-t-il des fraudes dans les élections ?",
        "Circonscriptions où les pourcentages ne font pas 100%",
        "Participation anormalement élevée",
        "Votes suspects"
    ]
    
    print("="*80)
    print("🔬 TEST FRAUD ANALYZER")
    print("="*80)
    
    for q in test_questions:
        print(f"\n❓ Question: {q}")
        print("-"*80)
        
        result = analyzer.analyze(q)
        
        print(f"✅ Success: {result['success']}")
        print(f"🚨 Anomalies: {result['anomalies_found']}")
        print(f"📊 Type: {result['analysis_type']}")
        print(f"\n{result['summary']}")
        
        if result['anomalies_found']:
            print(f"\n📋 Résultats: {len(result['results'])} lignes")
            print(result['results'].head())


if __name__ == "__main__":
    main()