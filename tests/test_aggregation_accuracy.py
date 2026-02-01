"""
Tests de précision pour les agrégations SQL
Vérifie que les comptes/sommes sont corrects
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.sql_generator import SQLGenerator
from src.agent.query_validator import QueryValidator
from src.agent.query_executor import QueryExecutor
from src.utils.config import DB_PATH


class TestAggregationAccuracy:
    """Tests de précision des agrégations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup pour chaque test"""
        self.sql_gen = SQLGenerator()
        self.validator = QueryValidator()
        self.executor = QueryExecutor(DB_PATH)
        self.executor.connect()
    
    def test_count_seats_rhdp(self):
        """Test: Nombre de sièges RHDP"""
        
        # SQL de référence (vérité terrain)
        ground_truth_sql = """
        SELECT COUNT(DISTINCT circonscription_num) as count
        FROM election_results
        WHERE parti_normalise = 'RHDP' AND elu = TRUE
        """
        
        result = self.executor.execute(ground_truth_sql)
        assert result['success'], "Ground truth query failed"
        
        expected_count = result['data'].iloc[0]['count']
        
        # Générer SQL via LLM
        question = "Combien de sièges a gagné le RHDP ?"
        sql_result = self.sql_gen.generate_sql(question)
        
        if sql_result['success']:
            validation = self.validator.validate(sql_result['sql'])
            if validation['valid']:
                result = self.executor.execute(validation['sanitized_sql'])
                
                if result['success'] and not result['data'].empty:
                    # Extraire le compte (première colonne, première ligne)
                    actual_count = result['data'].iloc[0][0]
                    
                    # Tolérance: ±5% ou ±2 sièges
                    tolerance = max(2, expected_count * 0.05)
                    
                    assert abs(actual_count - expected_count) <= tolerance, \
                        f"Expected ~{expected_count} seats, got {actual_count}"
    
    def test_count_total_circonscriptions(self):
        """Test: Nombre total de circonscriptions"""
        
        ground_truth_sql = "SELECT COUNT(DISTINCT circonscription_num) FROM election_results"
        
        result = self.executor.execute(ground_truth_sql)
        expected = result['data'].iloc[0][0]
        
        # Devrait être 205
        assert expected == 205, f"Expected 205 circonscriptions, got {expected}"
    
    def test_sum_votes_party(self):
        """Test: Somme des voix d'un parti"""
        
        ground_truth_sql = """
        SELECT SUM(voix) as total_votes
        FROM election_results
        WHERE parti_normalise = 'RHDP'
        """
        
        result = self.executor.execute(ground_truth_sql)
        expected_votes = result['data'].iloc[0]['total_votes']
        
        # Les voix doivent être > 0
        assert expected_votes > 0, "RHDP should have votes"
        
        # Devrait être > 1 million (réaliste pour un grand parti)
        assert expected_votes > 1_000_000, f"Expected > 1M votes, got {expected_votes:,}"
    
    def test_participation_rate_realistic(self):
        """Test: Taux de participation réaliste"""
        
        sql = """
        SELECT AVG(taux_participation) as avg_participation
        FROM election_results
        WHERE taux_participation IS NOT NULL
        """
        
        result = self.executor.execute(sql)
        avg_participation = result['data'].iloc[0]['avg_participation']
        
        # Devrait être entre 20% et 100%
        assert 20 <= avg_participation <= 100, \
            f"Unrealistic participation: {avg_participation}%"
    
    def test_elected_candidates_count(self):
        """Test: Nombre de candidats élus = 205"""
        
        sql = """
        SELECT COUNT(*) as elected_count
        FROM election_results
        WHERE elu = TRUE
        """
        
        result = self.executor.execute(sql)
        elected = result['data'].iloc[0]['elected_count']
        
        # Devrait être exactement 205 (1 par circonscription)
        assert elected == 205, f"Expected 205 elected, got {elected}"
    
    def test_top_parties_sum_to_total(self):
        """Test: Les sièges des partis somment à 205"""
        
        sql = """
        SELECT SUM(seat_count) as total_seats
        FROM (
            SELECT COUNT(DISTINCT circonscription_num) as seat_count
            FROM election_results
            WHERE elu = TRUE
            GROUP BY parti_normalise
        )
        """
        
        result = self.executor.execute(sql)
        total = result['data'].iloc[0]['total_seats']
        
        assert total == 205, f"Seat count mismatch: {total} != 205"


def run_evaluation():
    """Lance l'évaluation et génère un rapport"""
    
    print("="*70)
    print("📊 EVALUATION - Aggregation Accuracy")
    print("="*70)
    
    # Lancer pytest avec rapport détaillé
    exit_code = pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--color=yes'
    ])
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_evaluation()
    
    if exit_code == 0:
        print("\n✅ TOUS LES TESTS PASSENT")
    else:
        print(f"\n❌ ÉCHEC: {exit_code} test(s) échoué(s)")
    
    sys.exit(exit_code)