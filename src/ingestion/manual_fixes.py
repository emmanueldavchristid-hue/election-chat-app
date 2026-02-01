"""
CORRECTIONS MANUELLES FINALES
Corrige les erreurs de voix et candidats manquants identifiés
"""

import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_circonscription_5(df: pd.DataFrame) -> pd.DataFrame:
    """Correction des pourcentages pour circonscription 5"""
    logger.info("📌 Correction circ 5: Recalcul des pourcentages")
    
    corrections = {
        1127: 10.81,
        1710: 16.41,
        1417: 13.60,
        580: 5.57,
        3574: 34.30,
        157: 1.51,
        64: 0.61,
        32: 0.31,
        1626: 15.60
    }
    
    for voix, new_pct in corrections.items():
        mask = (df['circonscription_num'] == 5) & (df['voix'] == voix)
        if mask.any():
            df.loc[mask, 'pourcentage_voix'] = new_pct
    
    logger.info("  ✅ Circ 5: Pourcentages corrigés")
    return df


def fix_circonscription_6(df: pd.DataFrame) -> pd.DataFrame:
    """Ajouter les 6 candidats manquants à la circonscription 6"""
    logger.info("📌 Correction circ 6: Ajout des candidats manquants")
    
    # Supprimer toutes les lignes actuelles de circ 6
    df = df[df['circonscription_num'] != 6]
    
    # Données complètes pour circ 6
    circ6_data = [
        {'parti': 'RHDP', 'candidat': 'KANGBE YAYORO CHARLES LOPEZ', 'voix': 3169, 'pourcentage': 35.46, 'elu': True},
        {'parti': 'ADCI', 'candidat': 'CAMARA ISSOUF', 'voix': 1848, 'pourcentage': 20.68, 'elu': False},
        {'parti': 'INDEPENDANT', 'candidat': 'TANOH AMOI CHRISTIAN', 'voix': 88, 'pourcentage': 0.98, 'elu': False},
        {'parti': 'INDEPENDANT', 'candidat': 'GOUHAN EKANZA JULES ROLAND MONSIHO', 'voix': 282, 'pourcentage': 3.16, 'elu': False},
        {'parti': 'INDEPENDANT', 'candidat': "N'GUESSAN AUGUSTIN KOUAKOU KASSI", 'voix': 868, 'pourcentage': 9.71, 'elu': False},
        {'parti': 'INDEPENDANT', 'candidat': 'KOUAKOU NGORAN JEROME', 'voix': 126, 'pourcentage': 1.41, 'elu': False},
        {'parti': 'CNPCIN', 'candidat': 'YAO CHRIST FRANCIS ALAIN GILLES', 'voix': 110, 'pourcentage': 1.23, 'elu': False},
        {'parti': 'PDCI-RDA', 'candidat': 'OBOUMOU GOLE MARCELIN', 'voix': 2375, 'pourcentage': 26.57, 'elu': False},
    ]
    
    for cand in circ6_data:
        new_row = pd.Series({
            'region': 'AGNEBY-TIASSA',
            'circonscription_num': 6,
            'circonscription_name': "GBOLOUVILLE ET N'DOUCI, COMMUNES ET SOUS-PREFECTURES",
            'nb_bureaux': 118,
            'inscrits': 37720,
            'votants': 9324,
            'taux_participation': 24.72,
            'bulletins_nuls': 373,
            'suffrages_exprimes': 8951,
            'bulletins_blancs_nombre': 16,
            'bulletins_blancs_pourcentage': 0.18,
            'parti': cand['parti'],
            'candidat': cand['candidat'],
            'voix': cand['voix'],
            'pourcentage_voix': cand['pourcentage'],
            'elu': cand['elu'],
            'parti_normalise': cand['parti'],
            'candidat_normalise': cand['candidat'],
            'region_normalise': 'AGNEBY-TIASSA'
        })
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    logger.info("  ✅ Circ 6: 8 candidats ajoutés")
    return df


def fix_circonscription_60(df: pd.DataFrame) -> pd.DataFrame:
    """Supprimer les 2 candidats en trop de la circonscription 60"""
    logger.info("📌 Correction circ 60: Suppression candidats en trop")
    
    # Garder seulement le candidat RHDP avec 111618 voix
    df = df[~((df['circonscription_num'] == 60) & (df['voix'].isin([692, 300])))]
    
    # Corriger le pourcentage du candidat restant
    mask = (df['circonscription_num'] == 60) & (df['voix'] == 111618)
    df.loc[mask, 'pourcentage_voix'] = 98.95
    
    logger.info("  ✅ Circ 60: 2 candidats supprimés, pourcentage corrigé")
    return df


def fix_circonscription_61(df: pd.DataFrame) -> pd.DataFrame:
    """Ajouter les 2 candidats manquants et corriger les voix pour circ 61"""
    logger.info("📌 Correction circ 61: Ajout candidats + correction voix")
    
    # Supprimer toutes les lignes actuelles de circ 61
    df = df[df['circonscription_num'] != 61]
    
    # Données complètes pour circ 61
    circ61_data = [
        {'parti': 'CODE', 'candidat': 'OSONS LE CHANGEMENT', 'voix': 692, 'pourcentage': 6.10, 'elu': False},
        {'parti': 'GP-PAIX', 'candidat': 'PAIX-UNITE-PROSPERITE', 'voix': 300, 'pourcentage': 2.64, 'elu': False},
        {'parti': 'INDEPENDANT', 'candidat': 'VISION, INTEGRITE, ESPOIR', 'voix': 940, 'pourcentage': 8.28, 'elu': False},
        {'parti': 'RHDP', 'candidat': 'UNE COTE D"IVOIRE EN PAIX,PROSPERE ET SOLIDAIRE', 'voix': 5421, 'pourcentage': 47.77, 'elu': True},
        {'parti': 'PDCI-RDA', 'candidat': "TOUS ENSEMBLE POUR LA CÔTE D'IVOIRE", 'voix': 3771, 'pourcentage': 33.23, 'elu': False},
        {'parti': 'INDEPENDANT', 'candidat': 'UNION-DYNAMISME-ENTRAIDE', 'voix': 81, 'pourcentage': 0.71, 'elu': False},
    ]
    
    for cand in circ61_data:
        new_row = pd.Series({
            'region': 'GBEKE',
            'circonscription_num': 61,
            'circonscription_name': 'BOUNDA, BROBO ET MAMINI, COMMUNES ET SOUS-PREFECTURES',
            'nb_bureaux': 136,
            'inscrits': 29385,
            'votants': 11859,
            'taux_participation': 40.36,
            'bulletins_nuls': 511,
            'suffrages_exprimes': 11348,
            'bulletins_blancs_nombre': 143,
            'bulletins_blancs_pourcentage': 1.26,
            'parti': cand['parti'],
            'candidat': cand['candidat'],
            'voix': cand['voix'],
            'pourcentage_voix': cand['pourcentage'],
            'elu': cand['elu'],
            'parti_normalise': cand['parti'],
            'candidat_normalise': cand['candidat'],
            'region_normalise': 'GBEKE'
        })
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    logger.info("  ✅ Circ 61: 6 candidats ajoutés avec voix correctes")
    return df


def fix_circonscription_64(df: pd.DataFrame) -> pd.DataFrame:
    """Correction des pourcentages pour circonscription 64"""
    logger.info("📌 Correction circ 64: Recalcul des pourcentages")
    
    corrections = {
        4897: 71.90,
        411: 6.03,
        1385: 20.33
    }
    
    for voix, new_pct in corrections.items():
        mask = (df['circonscription_num'] == 64) & (df['voix'] == voix)
        if mask.any():
            df.loc[mask, 'pourcentage_voix'] = new_pct
    
    logger.info("  ✅ Circ 64: Pourcentages corrigés")
    return df


def fix_circonscription_65(df: pd.DataFrame) -> pd.DataFrame:
    """Ajouter les 4 candidats manquants à la circonscription 65"""
    logger.info("📌 Correction circ 65: Ajout des candidats manquants")
    
    # Ajouter les 4 candidats manquants
    missing_candidates = [
        {'parti': 'RHDP', 'candidat': 'FREGBO GUETE BASILE MESMIN', 'voix': 2632, 'pourcentage': 35.99, 'elu': False},
        {'parti': 'UDCY', 'candidat': "GOUHIZOUN N'DA PATRICK JEAN KOUAME", 'voix': 74, 'pourcentage': 1.01, 'elu': False},
        {'parti': 'INDEPENDANT', 'candidat': 'DIAKITE MOHAMED', 'voix': 111, 'pourcentage': 1.52, 'elu': False},
        {'parti': 'PDCI-RDA', 'candidat': 'GOUDARD AGOUA MOISE-HONORAT', 'voix': 403, 'pourcentage': 5.51, 'elu': False},
    ]
    
    for cand in missing_candidates:
        new_row = pd.Series({
            'region': 'GBOKLE',
            'circonscription_num': 65,
            'circonscription_name': 'GRIHIRI, LOBAKUYA, MEDON ET SASSANDRA, COMMUNES ET SOUS-PREFECTURES',
            'nb_bureaux': 104,
            'inscrits': 29913,
            'votants': 7502,
            'taux_participation': 25.08,
            'bulletins_nuls': 189,
            'suffrages_exprimes': 7313,
            'bulletins_blancs_nombre': 61,
            'bulletins_blancs_pourcentage': 0.83,
            'parti': cand['parti'],
            'candidat': cand['candidat'],
            'voix': cand['voix'],
            'pourcentage_voix': cand['pourcentage'],
            'elu': cand['elu'],
            'parti_normalise': cand['parti'],
            'candidat_normalise': cand['candidat'],
            'region_normalise': 'GBOKLE'
        })
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    logger.info("  ✅ Circ 65: 4 candidats ajoutés")
    return df


def fix_circonscription_114(df: pd.DataFrame) -> pd.DataFrame:
    """Correction des pourcentages pour circonscription 114"""
    logger.info("📌 Correction circ 114: Recalcul des pourcentages")
    
    corrections = {
        1039: 8.91,
        1006: 8.62,
        5872: 50.33,
        76: 0.65,
        3626: 31.08
    }
    
    for voix, new_pct in corrections.items():
        mask = (df['circonscription_num'] == 114) & (df['voix'] == voix)
        if mask.any():
            df.loc[mask, 'pourcentage_voix'] = new_pct
    
    logger.info("  ✅ Circ 114: Pourcentages corrigés")
    return df


def fix_circonscription_115(df: pd.DataFrame) -> pd.DataFrame:
    """Ajouter le candidat manquant à la circonscription 115"""
    logger.info("📌 Correction circ 115: Ajout candidat PDCI-RDA")
    
    # Ajouter le candidat PDCI-RDA manquant
    new_candidate = pd.Series({
        'region': 'INDENIE-DJUABLIN',
        'circonscription_num': 115,
        'circonscription_name': 'ABENGOUROU, SOUS-PREFECTURE, AMELEKIA, ANIANSSUE, EBILASSOKRO, NIABLE, YAKASSE-FEYASSE ET ZARANOU, COMMUNES ET SOUS-PREFECTURES',
        'nb_bureaux': 166,
        'inscrits': 51273,
        'votants': 22283,
        'taux_participation': 43.46,
        'bulletins_nuls': 498,
        'suffrages_exprimes': 21785,
        'bulletins_blancs_nombre': 104,
        'bulletins_blancs_pourcentage': 0.48,
        'parti': 'PDCI-RDA',
        'candidat': "TOUS ENSEMBLE POUR LA CÔTE D'IVOIRE",
        'voix': 3760,
        'pourcentage_voix': 17.26,
        'elu': False,
        'parti_normalise': 'PDCI-RDA',
        'candidat_normalise': "Tous Ensemble Pour La Côte D'Ivoire",
        'region_normalise': 'INDENIE-DJUABLIN'
    })
    
    df = pd.concat([df, pd.DataFrame([new_candidate])], ignore_index=True)
    
    logger.info("  ✅ Circ 115: Candidat PDCI-RDA ajouté")
    return df


def fix_circonscription_134(df: pd.DataFrame) -> pd.DataFrame:
    """Correction des pourcentages pour circonscription 134"""
    logger.info("📌 Correction circ 134: Recalcul des pourcentages")
    
    corrections = {
        131: 1.10,
        556: 4.66,
        209: 1.75,
        90: 0.75,
        254: 2.13,
        106: 0.89,
        146: 1.22,
        6712: 56.20,
        190: 1.59,
        24: 0.20,
        2511: 21.02,
        924: 7.74
    }
    
    for voix, new_pct in corrections.items():
        mask = (df['circonscription_num'] == 134) & (df['voix'] == voix)
        if mask.any():
            df.loc[mask, 'pourcentage_voix'] = new_pct
    
    logger.info("  ✅ Circ 134: Pourcentages corrigés")
    return df


def fix_circonscription_135(df: pd.DataFrame) -> pd.DataFrame:
    """Ajouter les 3 candidats manquants à la circonscription 135"""
    logger.info("📌 Correction circ 135: Ajout des candidats manquants")
    
    # Ajouter les 3 candidats manquants
    missing_candidates = [
        {'parti': 'INDEPENDANT', 'candidat': 'ZORO BI BALLO FRANCK', 'voix': 216, 'pourcentage': 2.50, 'elu': False},
        {'parti': 'PDCI-RDA', 'candidat': 'TRAZIE BI GUESSAN', 'voix': 2570, 'pourcentage': 29.75, 'elu': False},
        {'parti': 'MGC', 'candidat': 'KOUAME BI BLI ROBERT', 'voix': 92, 'pourcentage': 1.06, 'elu': False},
    ]
    
    for cand in missing_candidates:
        new_row = pd.Series({
            'region': 'MARAHOUE',
            'circonscription_num': 135,
            'circonscription_name': 'BONON ET ZAGUIETA, COMMUNES ET SOUS-PREFECTURES',
            'nb_bureaux': 112,
            'inscrits': 35059,
            'votants': 8815,
            'taux_participation': 25.14,
            'bulletins_nuls': 175,
            'suffrages_exprimes': 8640,
            'bulletins_blancs_nombre': 109,
            'bulletins_blancs_pourcentage': 1.26,
            'parti': cand['parti'],
            'candidat': cand['candidat'],
            'voix': cand['voix'],
            'pourcentage_voix': cand['pourcentage'],
            'elu': cand['elu'],
            'parti_normalise': cand['parti'],
            'candidat_normalise': cand['candidat'],
            'region_normalise': 'MARAHOUE'
        })
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    logger.info("  ✅ Circ 135: 3 candidats ajoutés")
    return df


def fix_circonscription_181(df: pd.DataFrame) -> pd.DataFrame:
    """Correction des pourcentages pour circonscription 181"""
    logger.info("📌 Correction circ 181: Recalcul des pourcentages")
    
    corrections = {
        8047: 57.95,
        5195: 37.41,
        32: 0.23,
        432: 3.11,
        133: 0.96
    }
    
    for voix, new_pct in corrections.items():
        mask = (df['circonscription_num'] == 181) & (df['voix'] == voix)
        if mask.any():
            df.loc[mask, 'pourcentage_voix'] = new_pct
    
    logger.info("  ✅ Circ 181: Pourcentages corrigés")
    return df


def fix_circonscription_182(df: pd.DataFrame) -> pd.DataFrame:
    """Correction des pourcentages pour circonscription 182"""
    logger.info("📌 Correction circ 182: Recalcul des pourcentages")
    
    corrections = {
        746: 6.00,
        1033: 8.30,
        1599: 12.85,
        2018: 16.22,
        171: 1.37,
        709: 5.70,
        220: 1.77,
        5893: 47.38
    }
    
    for voix, new_pct in corrections.items():
        mask = (df['circonscription_num'] == 182) & (df['voix'] == voix)
        if mask.any():
            df.loc[mask, 'pourcentage_voix'] = new_pct
    
    logger.info("  ✅ Circ 182: Pourcentages corrigés")
    return df


def apply_manual_fixes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique toutes les corrections manuelles
    """
    logger.info("🔧 APPLICATION DES CORRECTIONS MANUELLES")
    logger.info("="*70)
    
    df = df.copy()
    
    # Appliquer toutes les corrections
    df = fix_circonscription_5(df)
    df = fix_circonscription_6(df)
    df = fix_circonscription_60(df)
    df = fix_circonscription_61(df)
    df = fix_circonscription_64(df)
    df = fix_circonscription_65(df)
    df = fix_circonscription_114(df)
    df = fix_circonscription_115(df)
    df = fix_circonscription_134(df)
    df = fix_circonscription_135(df)
    df = fix_circonscription_181(df)
    df = fix_circonscription_182(df)
    
    # Validation finale
    logger.info("\n✔️ VALIDATION FINALE...")
    
    winners = df[df['elu']].groupby('circonscription_num').size()
    multiple = winners[winners > 1]
    none = set(df['circonscription_num'].unique()) - set(winners.index)
    
    if len(multiple) > 0:
        logger.warning(f"  ⚠️ {len(multiple)} circonscriptions avec plusieurs élus: {list(multiple.index)}")
    else:
        logger.info("  ✅ Chaque circonscription a max 1 élu")
    
    if len(none) > 0:
        logger.warning(f"  ⚠️ {len(none)} circonscriptions sans élu")
    else:
        logger.info("  ✅ Toutes les circonscriptions ont un élu")
    
    logger.info(f"\n✅ Total lignes: {len(df)}")
    logger.info(f"✅ Total circonscriptions: {df['circonscription_num'].nunique()}")
    logger.info(f"✅ Total élus: {df['elu'].sum()}")
    
    return df


def main():
    """Point d'entrée principal"""
    from src.utils.config import CSV_PATH, PARQUET_PATH
    
    # Charger données
    logger.info(f"📂 Chargement: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    logger.info(f"✅ {len(df)} lignes chargées\n")
    
    # Appliquer corrections
    df_fixed = apply_manual_fixes(df)
    
    # Sauvegarder
    logger.info("\n💾 Sauvegarde...")
    df_fixed.to_csv(CSV_PATH, index=False, encoding='utf-8')
    df_fixed.to_parquet(PARQUET_PATH, index=False)
    
    logger.info(f"✅ CSV: {CSV_PATH}")
    logger.info(f"✅ Parquet: {PARQUET_PATH}")
    
    logger.info("\n" + "="*70)
    logger.info("✅ CORRECTIONS MANUELLES TERMINÉES!")
    logger.info("="*70)
    
    logger.info("\n➡️ Prochaines étapes:")
    logger.info("  1. del data\\processed\\elections.duckdb")
    logger.info("  2. python -m src.ingestion.db_loader")
    logger.info("  3. streamlit run src\\app\\streamlit_app.py")


if __name__ == "__main__":
    main()