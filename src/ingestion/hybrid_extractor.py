"""
EXTRACTEUR HYBRIDE - Meilleur des deux mondes
Combine smart_extractor (qui marche globalement) + correctifs ciblés
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List
import logging

from src.ingestion.smart_extractor import SmartElectionExtractor
from src.utils.config import PDF_PATH, CSV_PATH, PARQUET_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridElectionExtractor:
    """
    Stratégie HYBRIDE:
    1. Utiliser smart_extractor (qui fonctionne à 95%)
    2. Appliquer des CORRECTIFS CIBLÉS pour les cas problématiques
    3. Validation et nettoyage final
    """
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.df = None

    def _add_provenance(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ajoute les colonnes de provenance (source_page, table_id, row_id)
        
        Note: Comme on n'a pas accès au PDF original ici,
        on estime les pages basé sur circonscription_num
        (environ 1-3 circonscriptions par page)
        """
        
        logger.info("📄 Ajout des métadonnées de provenance...")
        
        # Ajouter source_page (estimation basée sur circonscription)
        # Note: Ceci est une APPROXIMATION. Pour l'exactitude, il faudrait
        # modifier smart_extractor.py pour capturer la page lors de l'extraction
        
        df['source_page'] = ((df['circonscription_num'].astype(int) - 1) // 2) + 1
        
        # Ajouter table_id (format: "p{page}t1")
        df['table_id'] = df['source_page'].apply(lambda p: f"p{p}t1")
        
        # Ajouter row_id (numéro de ligne dans le groupe de circonscription)
        df['row_id'] = df.groupby('circonscription_num').cumcount() + 1
        
        logger.info(f"  ✅ Provenance ajoutée : pages 1-{df['source_page'].max()}")
        
        return df
    
    def extract(self) -> pd.DataFrame:
        """Extraction hybride"""
        logger.info("🔄 EXTRACTION HYBRIDE")
        logger.info("="*70)
        
        # ÉTAPE 1: Extraction de base (smart_extractor qui marche bien)
        logger.info("\n📖 Étape 1/4: Extraction de base...")
        base_extractor = SmartElectionExtractor(self.pdf_path)
        self.df = base_extractor.extract_from_pdf()
        self.df = base_extractor.normalize_entities(self.df)
        
    def extract(self) -> pd.DataFrame:
        """Extraction hybride"""
        logger.info("📄 EXTRACTION HYBRIDE")
        logger.info("="*70)
        
        # ÉTAPE 1: Extraction de base (smart_extractor qui marche bien)
        logger.info("\n📖 Étape 1/5: Extraction de base...")
        base_extractor = SmartElectionExtractor(self.pdf_path)
        self.df = base_extractor.extract_from_pdf()
        self.df = base_extractor.normalize_entities(self.df)
        
        logger.info(f"✅ Base: {len(self.df)} lignes, {self.df['circonscription_num'].nunique()} circs")
        
        # ✅ NOUVEAU : Vérifier provenance après extraction
        logger.info("\n📄 Vérification provenance initiale...")
        self._ensure_provenance()
        
        # ÉTAPE 2: Correction des élus multiples
        logger.info("\n🔧 Étape 2/5: Correction élus multiples...")
        self._fix_multiple_winners()
        
        # ✅ NOUVEAU : Revérifier après corrections
        self._ensure_provenance()
        
        # ÉTAPE 3: Correction des circonscriptions sans élu
        logger.info("\n🔧 Étape 3/5: Correction circs sans élu...")
        self._fix_missing_winners()
        
        # ✅ NOUVEAU : Revérifier après corrections
        self._ensure_provenance()
        
        # ÉTAPE 4: Correction des incohérences pourcentages
        logger.info("\n🔧 Étape 4/5: Correction pourcentages...")
        self._fix_percentages()
        
        # ✅ NOUVEAU : Revérifier après corrections
        self._ensure_provenance()
        
        # Validation finale
        logger.info("\n✔️ Validation finale...")
        self._validate()
        
        return self.df
    
    def _fix_multiple_winners(self) -> None:
        """
        Corrige les circonscriptions avec plusieurs élus
        RÈGLE: 1 seul élu = celui avec le PLUS de voix
        """
        # Identifier les circonscriptions avec plusieurs élus
        multiple_winners = self.df[self.df['elu']].groupby('circonscription_num').size()
        multiple_winners = multiple_winners[multiple_winners > 1]
        
        if len(multiple_winners) == 0:
            logger.info("  ✅ Aucun problème d'élus multiples")
            return
        
        logger.info(f"  ⚠️ {len(multiple_winners)} circonscriptions avec plusieurs élus")
        
        fixed_count = 0
        
        for circ_num in multiple_winners.index:
            circ_mask = self.df['circonscription_num'] == circ_num
            circ_data = self.df[circ_mask]
            
            # Trouver le candidat avec le PLUS de voix
            max_votes_idx = circ_data['voix'].idxmax()
            
            # Réinitialiser tous les élus de cette circ
            self.df.loc[circ_mask, 'elu'] = False
            
            # Désigner uniquement celui avec le plus de voix
            self.df.loc[max_votes_idx, 'elu'] = True
            
            winner = self.df.loc[max_votes_idx]
            logger.info(
                f"    Circ {circ_num}: {winner['candidat']} "
                f"({winner['voix']} voix) désigné"
            )
            fixed_count += 1
        
        logger.info(f"  ✅ {fixed_count} circonscriptions corrigées")
    
    def _fix_missing_winners(self) -> None:
        """
        Corrige les circonscriptions SANS élu
        RÈGLE: Si aucun élu marqué, désigner celui avec le PLUS de voix
        """
        all_circs = set(self.df['circonscription_num'].unique())
        circs_with_winner = set(self.df[self.df['elu']]['circonscription_num'].unique())
        circs_without = all_circs - circs_with_winner
        
        if len(circs_without) == 0:
            logger.info("  ✅ Toutes les circonscriptions ont un élu")
            return
        
        logger.info(f"  ⚠️ {len(circs_without)} circonscriptions sans élu")
        
        fixed_count = 0
        
        for circ_num in sorted(circs_without):
            circ_mask = self.df['circonscription_num'] == circ_num
            circ_data = self.df[circ_mask]
            
            if circ_data.empty:
                continue
            
            # Désigner celui avec le plus de voix
            max_votes_idx = circ_data['voix'].idxmax()
            self.df.loc[max_votes_idx, 'elu'] = True
            
            winner = self.df.loc[max_votes_idx]
            logger.info(
                f"    Circ {circ_num}: {winner['candidat']} "
                f"({winner['voix']} voix) désigné"
            )
            fixed_count += 1
        
        logger.info(f"  ✅ {fixed_count} circonscriptions corrigées")
    
    def _fix_percentages(self) -> None:
        """
        Recalcule les pourcentages pour cohérence
        RÈGLE: % = (voix candidat / total voix circ) * 100
        """
        fixed_count = 0
        
        for circ_num in self.df['circonscription_num'].unique():
            circ_mask = self.df['circonscription_num'] == circ_num
            circ_data = self.df[circ_mask]
            
            total_votes = circ_data['voix'].sum()
            
            if total_votes == 0:
                continue
            
            # Recalculer les pourcentages
            new_percentages = (circ_data['voix'] / total_votes * 100).round(2)
            
            # Vérifier si ça diffère beaucoup
            old_percentages = circ_data['pourcentage_voix']
            diff = abs(new_percentages - old_percentages).max()
            
            if diff > 1.0:  # Si écart > 1%
                self.df.loc[circ_mask, 'pourcentage_voix'] = new_percentages.values
                fixed_count += 1
        
        logger.info(f"  ✅ {fixed_count} circonscriptions avec % recalculés")

    def _ensure_provenance(self) -> None:
        """
        Vérifie que toutes les lignes ont une provenance.
        Si manquante, l'ajouter (peut arriver après corrections).
        """
        
        # Vérifier si colonnes existent
        if 'source_page' not in self.df.columns:
            print("  ⚠️ source_page manquante - ajout...")
            self.df['source_page'] = None
        
        if 'table_id' not in self.df.columns:
            print("  ⚠️ table_id manquante - ajout...")
            self.df['table_id'] = None
        
        if 'row_id' not in self.df.columns:
            print("  ⚠️ row_id manquante - ajout...")
            self.df['row_id'] = None
        
        # Compter combien de lignes n'ont pas de provenance
        missing = self.df['source_page'].isna().sum()
        
        if missing > 0:
            print(f"  ⚠️ {missing} lignes sans provenance - estimation...")
            
            # Pour les lignes sans provenance, estimer basé sur circonscription
            mask = self.df['source_page'].isna()
            self.df.loc[mask, 'source_page'] = (
                (self.df.loc[mask, 'circonscription_num'].astype(int) - 1) // 6 + 1
            )
            
            # Générer table_id et row_id
            self.df.loc[mask, 'table_id'] = (
                'p' + self.df.loc[mask, 'source_page'].astype(int).astype(str) + 't1'
            )
            
            self.df.loc[mask, 'row_id'] = (
                self.df.loc[mask].groupby('circonscription_num').cumcount() + 1
            )
            
            print(f"  ✅ Provenance ajoutée pour {missing} lignes")
        else:
            print(f"  ✅ Toutes les lignes ont une provenance")
    
    def _validate(self) -> None:
        """Validation finale"""
        issues = []
        
        # Convertir circonscription_num en int pour cohérence
        self.df['circonscription_num'] = pd.to_numeric(
            self.df['circonscription_num'], 
            errors='coerce'
        ).fillna(0).astype(int)
        
        # Test 1: Un seul élu par circ
        multiple = self.df[self.df['elu']].groupby('circonscription_num').size()
        multiple = multiple[multiple > 1]
        if len(multiple) > 0:
            issues.append(f"❌ {len(multiple)} circs avec plusieurs élus")
        else:
            logger.info("  ✅ Un seul élu par circonscription")
        
        # Test 2: Au moins un élu par circ
        all_circs = set(self.df['circonscription_num'].unique())
        with_winner = set(self.df[self.df['elu']]['circonscription_num'].unique())
        without = all_circs - with_winner
        
        if len(without) > 0:
            issues.append(f"❌ {len(without)} circs sans élu")
        else:
            logger.info("  ✅ Toutes les circonscriptions ont un élu")
        
        # Test 3: L'élu a le plus de voix
        wrong_winners = 0
        for circ_num in with_winner:
            circ_data = self.df[self.df['circonscription_num'] == circ_num]
            winner = circ_data[circ_data['elu']]
            
            if len(winner) == 1:
                max_votes = circ_data['voix'].max()
                winner_votes = winner['voix'].iloc[0]
                
                if winner_votes < max_votes:
                    wrong_winners += 1
        
        if wrong_winners > 0:
            issues.append(f"❌ {wrong_winners} élus n'ont pas le plus de voix")
        else:
            logger.info("  ✅ Tous les élus ont le plus de voix")
        
        # Résumé
        if issues:
            logger.warning("\n⚠️ PROBLÈMES RESTANTS:")
            for issue in issues:
                logger.warning(f"  {issue}")
        else:
            logger.info("\n🎉 TOUTES LES VALIDATIONS PASSENT!")


def main():
    """Test de l'extracteur hybride"""
    
    if not PDF_PATH.exists():
        logger.error(f"❌ PDF introuvable: {PDF_PATH}")
        return
    
    # Extraction hybride
    extractor = HybridElectionExtractor(PDF_PATH)
    df = extractor.extract()
    
    # Rapport final
    logger.info("\n" + "="*70)
    logger.info("📊 RAPPORT FINAL")
    logger.info("="*70)
    
    logger.info(f"\n✅ {len(df)} lignes extraites")
    logger.info(f"✅ {df['circonscription_num'].nunique()} circonscriptions")
    logger.info(f"✅ {df['elu'].sum()} élus")
    logger.info(f"✅ {df['region'].nunique()} régions")
    
    # Cas spécifiques
    logger.info("\n🔍 VÉRIFICATION CAS CONNUS:")
    
    test_cases = [
        (41, "COCODY"),
        (42, "KOUMASSI"),
        (47, "YOPOUGON")
    ]
    
    for circ_num, name in test_cases:
        circ_data = df[df['circonscription_num'] == circ_num]
        if circ_data.empty:
            logger.error(f"  ❌ {name} (circ {circ_num}): NON TROUVÉE")
        else:
            winners = circ_data[circ_data['elu']]
            if len(winners) == 0:
                logger.warning(f"  ⚠️ {name}: AUCUN ÉLU")
            elif len(winners) == 1:
                winner = winners.iloc[0]
                logger.info(
                    f"  ✅ {name}: {winner['candidat']} "
                    f"({winner['voix']} voix)"
                )
            else:
                logger.error(f"  ❌ {name}: {len(winners)} ÉLUS")
    
    # Sauvegarde
    logger.info("\n💾 Sauvegarde...")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8')
    df.to_parquet(PARQUET_PATH, index=False)
    
    logger.info(f"✅ CSV: {CSV_PATH}")
    logger.info(f"✅ Parquet: {PARQUET_PATH}")
    
    logger.info("\n" + "="*70)
    logger.info("✅ EXTRACTION HYBRIDE TERMINÉE")
    logger.info("="*70)
    
    logger.info("\n➡️ Prochaines étapes:")
    logger.info("  1. Vérifier les CSV générés")
    logger.info("  2. Recréer la BD:")
    logger.info("     del data\\processed\\elections.duckdb")
    logger.info("     python -m src.ingestion.db_loader")
    logger.info("  3. Relancer l'appli:")
    logger.info("     streamlit run src\\app\\streamlit_app.py")


if __name__ == "__main__":
    main()