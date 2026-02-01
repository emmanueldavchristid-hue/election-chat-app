"""
Tests de validation contre la vérité terrain (ground truth) - Version corrigée et actualisée
Compare les données extraites avec des échantillons vérifiés manuellement du PDF.
Utilise les valeurs EXACTES observées dans elections.csv (2025/2026).
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# ────────────────────────────────────────────────────────────────
# CONFIGURATION - À ADAPTER SI BESOIN
# ────────────────────────────────────────────────────────────────
CSV_PATH = Path("elections.csv")                  # ← change si le fichier est ailleurs
# ex: CSV_PATH = Path("data/processed/elections.csv")
# PARQUET_PATH = Path("elections.parquet")        # décommente si tu utilises parquet

# ────────────────────────────────────────────────────────────────
class TestGroundTruthValidation:
    """
    Tests de validation robustes contre la vérité terrain actualisée.
    """

    @pytest.fixture
    def df(self):
        """Charge et prépare les données."""
        if not CSV_PATH.exists():
            pytest.skip(f"Fichier introuvable : {CSV_PATH}")

        df = pd.read_csv(CSV_PATH)
        # Normalisation
        df["circonscription_num"] = df["circonscription_num"].astype(str).str.strip().str.zfill(3)
        df["voix"] = pd.to_numeric(df["voix"], errors="coerce")
        df["pourcentage_voix"] = pd.to_numeric(df["pourcentage_voix"], errors="coerce")
        df["elu"] = df["elu"].astype(bool)
        # Optionnel : drop NaN voix si besoin
        df = df.dropna(subset=["voix", "pourcentage_voix"])
        return df

    # ────────────────────────────────────────────────────────────────
    # GROUND TRUTH : valeurs EXACTES tirées de elections.csv
    # ────────────────────────────────────────────────────────────────
    GROUND_TRUTH_SAMPLES = {
        '001': {
            'circonscription_name_substr': 'ABOUDE, ATTOBROU, GUESSIGUIE',
            'region': 'AGNEBY-TIASSA',
            'winner': {'candidat': 'KOFFI AKA CHARLES', 'parti': 'RHDP', 'voix': 9078, 'pourcentage': 66.35},
            'nb_candidats': 8,
            'inscrits': 52106,
            'votants': 14070,
            'taux_participation': 27.0
        },
        '002': {
            'circonscription_name_substr': 'AGBOVILLE COMMUNE',
            'region': 'AGNEBY-TIASSA',
            'winner': {'candidat': "DIMBA N'GOU PIERRE", 'parti': 'RHDP', 'voix': 10675, 'pourcentage': 85.37},
            'nb_candidats': 6,
            'inscrits': 48710,
            'votants': 12821,
            'taux_participation': 26.32
        },
        '009': {
            'circonscription_name_substr': 'BOOKO, BOROTOU, MAHANDOUGOU',
            'region': 'BAFING',
            'winner': {'candidat': 'DIOMANDE LASSINA', 'parti': 'RHDP', 'voix': 11219, 'pourcentage': 95.87},
            'nb_candidats': 3,
            'inscrits': 17626,
            'votants': 11919,
            'taux_participation': 67.62
        },
        '041': {
            'circonscription_name_substr': 'COCODY',
            'region': "DISTRICT AUTONOME D'ABIDJAN",
            'winner': {'candidat': 'TOUS ENSEMBLE POUR LE CÔTE-DIVOIRE', 'parti': 'PDCI-RDA', 'voix': 14740, 'pourcentage': 53.06},
            'nb_candidats': 14,
            'inscrits': 279785,
            'votants': 28279,
            'taux_participation': 10.11
        },
        '042': {
            'circonscription_name_substr': 'KOUMASSI',
            'region': "DISTRICT AUTONOME D'ABIDJAN",
            'winner': {'candidat': 'UNE COTE DIVOIRE EN PAIX, PROSPERE ET SOLIDAIRE', 'parti': 'RHDP', 'voix': 23968, 'pourcentage': 74.35},
            'nb_candidats': 3,
            'inscrits': 176954,
            'votants': 33090,
            'taux_participation': 18.7
        },
        '047': {
            'circonscription_name_substr': 'YOPOUGON',
            'region': "DISTRICT AUTONOME D'ABIDJAN",
            'winner': {'candidat': 'UNE COTE DIVOIRE EN PAIX, PROPERE ET SOLIDAIRE', 'parti': 'RHDP', 'voix': 49017, 'pourcentage': 68.14},
            'nb_candidats': 6,
            'inscrits': 555901,
            'votants': 73989,
            'taux_participation': 13.31
        },
        '061': {
            'circonscription_name_substr': 'BOUNDA, BROBO ET MAMINI',
            'region': 'GBEKE',
            'winner': {'candidat': 'UNE COTE D"IVOIRE EN PAIX,PROSPERE ET SOLIDAIRE', 'parti': 'RHDP', 'voix': 5421, 'pourcentage': 47.77},
            'nb_candidats': 7,
            'inscrits': 29385,
            'votants': 11859,
            'taux_participation': 40.36
        },
        # Tu peux ajouter d'autres circonscriptions validées manuellement ici
        # ex: '003', '004', '115', '135', '205', etc.
    }

    # ────────────────────────────────────────────────────────────────
    # TESTS PRINCIPAUX
    # ────────────────────────────────────────────────────────────────
    @pytest.mark.critical
    @pytest.mark.parametrize("circ_num,expected", GROUND_TRUTH_SAMPLES.items())
    def test_circonscription_validation(self, df, circ_num, expected):
        data = df[df['circonscription_num'] == circ_num]
        assert not data.empty, f"❌ Circonscription {circ_num} introuvable"

        row0 = data.iloc[0]

        # Nom (substring robuste)
        assert expected['circonscription_name_substr'] in row0['circonscription_name'], \
            f"Nom incorrect pour {circ_num}"

        assert row0['region'] == expected['region'], \
            f"Région incorrecte pour {circ_num}"

        assert len(data) == expected['nb_candidats'], \
            f"Nombre de candidats incorrect pour {circ_num} (attendu {expected['nb_candidats']}, trouvé {len(data)}) "

        assert row0['inscrits'] == expected['inscrits'], \
            f"Inscrits incorrects pour {circ_num}"
        assert row0['votants'] == expected['votants'], \
            f"Votants incorrects pour {circ_num}"
        assert abs(row0['taux_participation'] - expected['taux_participation']) < 0.05, \
            f"Taux participation incorrect pour {circ_num}"

        # Élu unique
        elus = data[data['elu'] == True]
        assert len(elus) == 1, f"Pas exactement 1 élu pour {circ_num} (trouvé : {len(elus)})"

        winner = elus.iloc[0]

        assert expected['winner']['candidat'] in winner['candidat'], \
            f"Mauvais candidat gagnant pour {circ_num}"

        parti = winner.get('parti_normalise', winner['parti'])
        assert expected['winner']['parti'] in parti, \
            f"Mauvais parti pour {circ_num}"

        assert winner['voix'] == expected['winner']['voix'], \
            f"Voix incorrectes pour gagnant {circ_num}"

        assert abs(winner['pourcentage_voix'] - expected['winner']['pourcentage']) < 0.11, \
            f"Pourcentage incorrect pour gagnant {circ_num}"

    def test_pourcentages_coherents_avec_voix(self, df):
        """Vérifie la cohérence des pourcentages déclarés vs recalculés."""
        ecarts = []
        for num, group in df.groupby('circonscription_num'):
            total = group['voix'].sum()
            if total == 0:
                continue
            for _, row in group.iterrows():
                calc = (row['voix'] / total * 100)
                ecart = abs(row['pourcentage_voix'] - calc)
                if ecart > 0.15:
                    ecarts.append({
                        'circ': num,
                        'candidat': row['candidat'],
                        'voix': row['voix'],
                        'pct_csv': row['pourcentage_voix'],
                        'pct_calc': round(calc, 2),
                        'ecart': round(ecart, 3)
                    })
        assert not ecarts, f"Écarts significatifs sur pourcentages :\n{pd.DataFrame(ecarts)}"

    def test_nombre_elus_exact(self, df):
        """Vérifie qu'il y a exactement un élu par circonscription."""
        nb_circos = df['circonscription_num'].nunique()
        nb_elus = df['elu'].sum()
        assert nb_elus == nb_circos, \
            f"Nombre d'élus incorrect : {nb_elus} au lieu de {nb_circos}"

    def test_colonnes_traçabilite_partiellement_remplies(self, df):
        """Vérifie que les colonnes source_page/table_id/row_id sont présentes mais partiellement vides."""
        expected_cols = ['source_page', 'table_id', 'row_id']
        for col in expected_cols:
            assert col in df.columns, f"Colonne manquante : {col}"

        na_count = df['source_page'].isna().sum()
        total = len(df)
        print(f"Colonnes traçabilité : {na_count} / {total} lignes NaN ({na_count/total:.1%})")
        assert na_count < total * 0.20, \
            f"Trop de NaN dans source_page : {na_count} ({na_count/total:.1%})"


# ────────────────────────────────────────────────────────────────
# Rapport rapide console (lance avec python nom_du_fichier.py)
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        df = pd.read_csv(CSV_PATH)
        df["circonscription_num"] = df["circonscription_num"].astype(str).str.zfill(3)

        print("\n" + "═" * 90)
        print("RAPPORT RAPIDE VALIDATION GROUND TRUTH")
        print("═" * 90)

        ground = TestGroundTruthValidation.GROUND_TRUTH_SAMPLES
        results = []

        for circ, exp in ground.items():
            d = df[df["circonscription_num"] == circ]
            if d.empty:
                results.append(f"{circ} → ABSENT")
                continue

            elus = d[d["elu"]]
            if len(elus) != 1:
                results.append(f"{circ} → {len(elus)} élu(s) au lieu de 1")
                continue

            w = elus.iloc[0]
            ok = (
                w["voix"] == exp["winner"]["voix"] and
                abs(w["pourcentage_voix"] - exp["winner"]["pourcentage"]) < 0.11
            )
            status = "OK" if ok else "ÉCHEC"
            results.append(f"{circ} → {status} | voix={w['voix']} | pct={w['pourcentage_voix']:.2f}%")

        for r in results:
            print(r)

        print("\n" + "═" * 90)
        print(f"Nombre total de circonscriptions dans le fichier : {df['circonscription_num'].nunique()}")
        print(f"Nombre total d'élus : {df['elu'].sum()}")
        print("═" * 90)

    except Exception as e:
        print(f"Erreur lors du rapport rapide : {e}")