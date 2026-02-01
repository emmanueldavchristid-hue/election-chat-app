"""
Smart extractor that understands the PDF structure.
Creates a clean, normalized dataset for election results.
"""
import pdfplumber
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Any

class SmartElectionExtractor:
    """Intelligent extractor for election results PDF."""
    
    # Cartographie exacte des régions par circonscription
    REGION_MAP = {
        range(1, 9): "AGNEBY-TIASSA",
        range(9, 14): "BAFING",
        range(14, 19): "BAGOUE",
        range(19, 23): "BELIER",
        range(23, 28): "BERE",
        range(28, 33): "BOUNKANI",
        range(33, 38): "CAVALLY",
        range(38, 51): "DISTRICT AUTONOME D'ABIDJAN",
        range(51, 54): "DISTRICT AUTONOME DE YAMOUSSOUKRO",
        range(54, 56): "FOLON",
        range(56, 64): "GBEKE",
        range(64, 67): "GBOKLE",
        range(67, 78): "GOH",
        range(78, 83): "GONTOUGO",
        range(83, 86): "GRANDS PONTS",
        range(86, 93): "GUEMON",
        range(93, 99): "HAMBOL",
        range(99, 109): "HAUT-SASSANDRA",
        range(109, 114): "IFFOU",
        range(114, 119): "INDENIE-DJUABLIN",
        range(119, 125): "KABADOUGOU",
        range(141, 148): "LA ME",
        range(125, 133): "LOH-DJIBOUA",
        range(133, 141): "MARAHOUE",
        range(148, 154): "NAWA",
        range(163, 173): "PORO",
        range(173, 178): "SAN-PEDRO",
        range(178, 185): "SUD-COMOE",
        range(185, 190): "TCHOLOGO",
        range(191, 200): "TONKPI",
        range(200, 206): "WORODOUGOU",
    }
    
    # MORONOU et N'ZI sont dispersés
    MORONOU_CIRCS = {154, 157, 158, 161, 162}
    NZI_CIRCS = {155, 156, 159, 160}
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.results = []
    
    def get_region_for_circonscription(self, circ_num: int) -> str:
        """Retourne la région pour un numéro de circonscription."""
        # Cas spéciaux
        if circ_num in self.MORONOU_CIRCS:
            return "MORONOU"
        if circ_num in self.NZI_CIRCS:
            return "N'ZI"
        
        # Recherche dans la carte
        for circ_range, region in self.REGION_MAP.items():
            if circ_num in circ_range:
                return region
        
        return "INCONNU"
        
    def clean_text(self, text: str) -> str:
        """Clean text by removing line breaks and extra spaces."""
        if not text or pd.isna(text):
            return ""
        return re.sub(r'\s+', ' ', str(text).replace('\n', ' ')).strip()
    
    def clean_number(self, text: str) -> int:
        """Convert text to integer, handling spaces."""
        if not text or pd.isna(text):
            return 0
        # Remove spaces and convert
        cleaned = str(text).replace(' ', '').replace('\xa0', '')
        try:
            return int(cleaned)
        except:
            return 0
    
    def clean_percentage(self, text: str) -> float:
        """Convert percentage text to float."""
        if not text or pd.isna(text):
            return 0.0
        # Remove % and convert
        cleaned = str(text).replace('%', '').replace(',', '.').strip()
        try:
            return float(cleaned)
        except:
            return 0.0
    
    def extract_from_pdf(self) -> pd.DataFrame:
        """Extract all election results from PDF."""
        print(f"📖 Opening PDF: {self.pdf_path}")
        
        current_circonscription = None
        
        with pdfplumber.open(self.pdf_path) as pdf:
            print(f"📄 Total pages: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages, 1):  # ← Déjà bon
                print(f"⏳ Processing page {page_num}/{len(pdf.pages)}...", end='\r')
                
                tables = page.extract_tables()
                
                for table_idx, table in enumerate(tables, start=1):  # ✅ MODIFIÉ
                    if not table or len(table) < 2:
                        continue
                    
                    # Skip header rows (first 2 rows are headers)
                    for row_idx, row in enumerate(table[2:], start=2):
                        # Skip empty rows
                        if not any(row):
                            continue
                        
                        # Clean and extract fields
                        circ_num = self.clean_text(row[1]) if len(row) > 1 else ""
                        circ_name = self.clean_text(row[2]) if len(row) > 2 else ""
                        
                        # NEW CIRCONSCRIPTION: Check if row[1] contains a number
                        if circ_num and circ_num.isdigit() and len(circ_num) <= 3:
                            circ_num_int = int(circ_num)
                            
                            # Utiliser la cartographie exacte pour obtenir la région
                            effective_region = self.get_region_for_circonscription(circ_num_int)
                            
                            # This is a new circonscription
                            current_circonscription = {
                                'region': effective_region,
                                'circonscription_num': circ_num,
                                'circonscription_name': circ_name,
                                'nb_bureaux': self.clean_number(row[3]) if len(row) > 3 else 0,
                                'inscrits': self.clean_number(row[4]) if len(row) > 4 else 0,
                                'votants': self.clean_number(row[5]) if len(row) > 5 else 0,
                                'taux_participation': self.clean_percentage(row[6]) if len(row) > 6 else 0.0,
                                'bulletins_nuls': self.clean_number(row[7]) if len(row) > 7 else 0,
                                'suffrages_exprimes': self.clean_number(row[8]) if len(row) > 8 else 0,
                                'bulletins_blancs_nombre': self.clean_number(row[9]) if len(row) > 9 else 0,
                                'bulletins_blancs_pourcentage': self.clean_percentage(row[10]) if len(row) > 10 else 0.0,
                            }
                            # IMPORTANT: Don't continue - still extract candidate from columns 11-15
                        
                        # Extract candidate information (from any row that has it)
                        parti = self.clean_text(row[11]) if len(row) > 11 else ""
                        candidat = self.clean_text(row[12]) if len(row) > 12 else ""
                        score = self.clean_number(row[13]) if len(row) > 13 else 0
                        pourcentage = self.clean_percentage(row[14]) if len(row) > 14 else 0.0
                        elu = self.clean_text(row[15]) if len(row) > 15 else ""
                        
                        # If we have candidate data and a current circonscription
                        if candidat and parti and current_circonscription:
                            result = {
                                **current_circonscription,
                                'parti': parti,
                                'candidat': candidat,
                                'voix': score,
                                'pourcentage_voix': pourcentage,
                                'elu': 'ELU(E)' in elu.upper() or 'ELU' in elu.upper(),
                                # ✅ NOUVEAU : Provenance PDF exacte
                                'source_page': page_num,
                                'table_id': f"p{page_num}t{table_idx}",
                                'row_id': row_idx,
                            }
                            self.results.append(result)
        
        print(f"\n✅ Extracted {len(self.results)} candidate results")
        
        # Convert to DataFrame
        df = pd.DataFrame(self.results)
        return df
    
    def normalize_entities(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize entity names (regions, parties, etc.)."""
        print("\n🧹 Normalizing entities...")
        
        # Normalize party names
        party_mapping = {
            'RHDP': 'RHDP',
            'R.H.D.P': 'RHDP',
            'R.H.D.P.': 'RHDP',
            'PDCI-RDA': 'PDCI-RDA',
            'PDCI': 'PDCI-RDA',
            'INDEPENDANT': 'INDEPENDANT',
            'INDÉPENDANT': 'INDEPENDANT',
        }
        
        df['parti_normalise'] = df['parti'].str.upper().str.strip()
        for old, new in party_mapping.items():
            df.loc[df['parti_normalise'] == old, 'parti_normalise'] = new
        
        # Normalize candidate names (remove extra spaces)
        df['candidat_normalise'] = df['candidat'].str.strip().str.title()
        
        # Normalize region names
        df['region_normalise'] = df['region'].str.upper().str.strip()
        
        print(f"✅ Unique parties: {df['parti_normalise'].nunique()}")
        print(f"✅ Unique regions: {df['region_normalise'].nunique()}")
        print(f"✅ Unique circonscriptions: {df['circonscription_num'].nunique()}")
        
        return df
    
    def get_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            'total_circonscriptions': df['circonscription_num'].nunique(),
            'total_candidats': len(df),
            'total_elus': df['elu'].sum(),
            'total_inscrits': df.groupby('circonscription_num')['inscrits'].first().sum(),
            'total_votants': df.groupby('circonscription_num')['votants'].first().sum(),
            'parties': df['parti_normalise'].value_counts().to_dict(),
        }

def main():
    """Test the smart extractor."""
    from src.utils.config import PDF_PATH, CSV_PATH, PARQUET_PATH
    
    if not PDF_PATH.exists():
        print(f"❌ PDF not found at {PDF_PATH}")
        print("Run: python scripts/download_pdf.py")
        return
    
    # Extract data
    extractor = SmartElectionExtractor(PDF_PATH)
    df = extractor.extract_from_pdf()
    
    if df.empty:
        print("❌ No data extracted")
        return
    
    # Normalize entities
    df = extractor.normalize_entities(df)
    
    # Show preview
    print("\n" + "="*70)
    print("📊 EXTRACTION PREVIEW")
    print("="*70)
    
    print(f"\n📋 Dataset Shape: {df.shape}")
    print(f"\n📋 Columns: {list(df.columns)}")
    
    print("\n📊 First 10 rows:")
    print(df.head(10))
    
    print("\n📊 Summary Statistics:")
    stats = extractor.get_summary_stats(df)
    for key, value in stats.items():
        if key != 'parties':
            print(f"  {key}: {value}")
    
    print("\n📊 Results by Party:")
    for party, count in stats['parties'].items():
        elus = df[(df['parti_normalise'] == party) & (df['elu'] == True)].shape[0]
        print(f"  {party}: {count} candidats, {elus} élu(s)")
    
    # Save to CSV and Parquet
    print("\n💾 Saving data...")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8')
    print(f"✅ Saved to CSV: {CSV_PATH}")
    
    df.to_parquet(PARQUET_PATH, index=False)
    print(f"✅ Saved to Parquet: {PARQUET_PATH}")
    
    print("\n" + "="*70)
    print("✅ EXTRACTION COMPLETE!")
    print("="*70)

if __name__ == "__main__":
    main()