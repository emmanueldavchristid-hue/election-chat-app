"""
Configuration pytest et fixtures partagées.
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Ajouter le dossier src au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import CSV_PATH, PARQUET_PATH, PDF_PATH


@pytest.fixture(scope="session")
def election_data():
    """Charge les données électorales extraites (partagé entre tous les tests)."""
    if CSV_PATH.exists():
        return pd.read_csv(CSV_PATH)
    elif PARQUET_PATH.exists():
        return pd.read_parquet(PARQUET_PATH)
    else:
        pytest.skip("Aucun fichier de données trouvé. Lancez d'abord l'extraction.")


@pytest.fixture(scope="session")
def pdf_path():
    """Retourne le chemin du PDF source."""
    if not PDF_PATH.exists():
        pytest.skip("PDF source non trouvé")
    return PDF_PATH


@pytest.fixture
def sample_circonscription_data(election_data):
    """Retourne les données d'une circonscription exemple."""
    # Prendre la première circonscription
    first_circ = election_data['circonscription_num'].iloc[0]
    return election_data[election_data['circonscription_num'] == first_circ].copy()


@pytest.fixture
def known_issues():
    """Liste des problèmes connus détectés manuellement."""
    return {
        'cocody': {
            'circonscription_contains': 'COCODY',
            'expected_winner_party': 'PDCI-RDA',
            'issue': 'Affiche 2 gagnants au lieu de 1'
        },
        'koumassi': {
            'circonscription_contains': 'KOUMASSI',
            'expected_has_winner': True,
            'issue': "N'affiche aucun gagnant"
        },
        'yopougon': {
            'circonscription_contains': 'YOPOUGON',
            'expected_has_winner': True,
            'issue': 'Affiche RHDP avec mauvais nombres de voix'
        }
    }


@pytest.fixture
def ground_truth_samples():
    """Échantillon de vérité terrain (à remplir manuellement depuis le PDF)."""
    # TODO: Remplir avec des cas réels du PDF pour validation
    return {
        'circonscription_001': {
            'name': 'ABOUDE, ATTOBROU, GUESSIGUIE...',
            'region': 'AGNEBY-TIASSA',
            'winner': {
                'candidat': 'KOFFI AKA CHARLES',
                'parti': 'RHDP',
                'voix': 9078,
                'pourcentage': 66.35
            },
            'total_candidats': 8,
            'inscrits': 25338,
            'votants': 14070
        },
        # Ajouter plus d'échantillons...
    }


def pytest_configure(config):
    """Configuration pytest personnalisée."""
    config.addinivalue_line(
        "markers", 
        "critical: marque les tests critiques qui doivent absolument passer"
    )
    config.addinivalue_line(
        "markers",
        "known_issue: marque les tests qui documentent des bugs connus"
    )
    config.addinivalue_line(
        "markers",
        "slow: marque les tests lents qui peuvent être skippés en dev"
    )


def pytest_collection_modifyitems(config, items):
    """Modifie la collection de tests."""
    # Ajouter le marker 'critical' automatiquement aux tests BusinessRules
    for item in items:
        if "TestBusinessRules" in str(item.parent):
            item.add_marker(pytest.mark.critical)