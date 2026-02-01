"""
Database loader for election results.
Creates and populates DuckDB database.
"""
import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional

class DatabaseLoader:
    """Load election data into DuckDB."""
    
    def __init__(self, db_path: Path):
        """Initialize database loader."""
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Connect to database."""
        print(f"🔌 Connecting to database: {self.db_path}")
        self.conn = duckdb.connect(str(self.db_path))
        print("✅ Connected")
    
    def create_schema(self, schema_path: Path):
        """Create database schema from SQL file."""
        if not schema_path.exists():
            print(f"❌ Schema file not found: {schema_path}")
            return False
        
        print(f"📋 Creating schema from: {schema_path}")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Execute schema creation
        self.conn.execute(schema_sql)
        print("✅ Schema created successfully")
        return True
    
    def load_data(self, csv_path: Path):
        """Load data from CSV into database."""
        if not csv_path.exists():
            print(f"❌ CSV file not found: {csv_path}")
            return False
        
        print(f"📊 Loading data from: {csv_path}")
        
        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"  Rows to load: {len(df)}")
        
        # ✅ VÉRIFIER SI PROVENANCE EXISTE DANS LE CSV
        has_provenance = all(col in df.columns for col in ['source_page', 'table_id', 'row_id'])
        
        if has_provenance:
            print(f"  ✅ Colonnes de provenance détectées dans le CSV")
        else:
            print(f"  ⚠️ Colonnes de provenance manquantes - ajout...")
            # Ajouter si manquantes
            if 'source_page' not in df.columns:
                df['source_page'] = ((df['circonscription_num'].astype(int) - 1) // 6 + 1)
            if 'table_id' not in df.columns:
                df['table_id'] = 'p' + df['source_page'].astype(int).astype(str) + 't1'
            if 'row_id' not in df.columns:
                df['row_id'] = df.groupby('circonscription_num').cumcount() + 1
        
        # Insert data with explicit column mapping (✅ AVEC PROVENANCE)
        self.conn.execute("""
            INSERT INTO election_results (
                id,
                region,
                region_normalise,
                circonscription_num,
                circonscription_name,
                nb_bureaux,
                inscrits,
                votants,
                taux_participation,
                bulletins_nuls,
                suffrages_exprimes,
                bulletins_blancs_nombre,
                bulletins_blancs_pourcentage,
                parti,
                parti_normalise,
                candidat,
                candidat_normalise,
                voix,
                pourcentage_voix,
                elu,
                source_page,
                table_id,
                row_id
            )
            SELECT 
                ROW_NUMBER() OVER () AS id,
                region,
                region_normalise,
                circonscription_num,
                circonscription_name,
                nb_bureaux,
                inscrits,
                votants,
                taux_participation,
                bulletins_nuls,
                suffrages_exprimes,
                bulletins_blancs_nombre,
                bulletins_blancs_pourcentage,
                parti,
                parti_normalise,
                candidat,
                candidat_normalise,
                voix,
                pourcentage_voix,
                elu,
                source_page,
                table_id,
                row_id
            FROM df
        """)
        
        # Verify
        count = self.conn.execute("SELECT COUNT(*) FROM election_results").fetchone()[0]
        print(f"✅ Loaded {count} rows into database")
        
        # ✅ VÉRIFIER QUE source_page EST BIEN CHARGÉ
        null_count = self.conn.execute(
            "SELECT COUNT(*) FROM election_results WHERE source_page IS NULL"
        ).fetchone()[0]
        
        if null_count > 0:
            print(f"  ⚠️ {null_count} lignes sans source_page")
        else:
            print(f"  ✅ Toutes les lignes ont source_page")
        
        # Afficher distribution pages
        page_stats = self.conn.execute("""
            SELECT 
                MIN(source_page) as min_page,
                MAX(source_page) as max_page,
                COUNT(DISTINCT source_page) as unique_pages
            FROM election_results
        """).fetchone()
        
        if page_stats and page_stats[0]:
            print(f"  📄 Pages : {page_stats[0]} → {page_stats[1]} ({page_stats[2]} pages uniques)")
        
        return True
    
    def create_indexes(self):
        """Create indexes for better performance."""
        print("🔍 Creating indexes...")
        # Indexes are already in schema.sql
        print("✅ Indexes created")
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}
        
        # Total records
        stats['total_records'] = self.conn.execute(
            "SELECT COUNT(*) FROM election_results"
        ).fetchone()[0]
        
        # Total circonscriptions
        stats['total_circonscriptions'] = self.conn.execute(
            "SELECT COUNT(DISTINCT circonscription_num) FROM election_results"
        ).fetchone()[0]
        
        # Total winners
        stats['total_winners'] = self.conn.execute(
            "SELECT COUNT(*) FROM election_results WHERE elu = TRUE"
        ).fetchone()[0]
        
        # Total parties
        stats['total_parties'] = self.conn.execute(
            "SELECT COUNT(DISTINCT parti_normalise) FROM election_results"
        ).fetchone()[0]
        
        # Top parties by seats
        stats['top_parties'] = self.conn.execute("""
            SELECT parti_normalise, COUNT(*) as sieges
            FROM election_results
            WHERE elu = TRUE
            GROUP BY parti_normalise
            ORDER BY sieges DESC
            LIMIT 5
        """).fetchall()
        
        return stats
    
    def test_views(self):
        """Test that views work correctly."""
        print("\n🧪 Testing views...")
        
        views = ['vw_winners', 'vw_party_results', 'vw_turnout', 
                 'vw_region_results', 'vw_close_races']
        
        for view in views:
            try:
                count = self.conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
                print(f"  ✅ {view}: {count} rows")
            except Exception as e:
                print(f"  ❌ {view}: {e}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("🔌 Database connection closed")

def main():
    """Load data into database."""
    from src.utils.config import DB_PATH, CSV_PATH, SCHEMA_DIR
    
    schema_path = SCHEMA_DIR / 'schema.sql'
    
    # Check if CSV exists
    if not CSV_PATH.exists():
        print(f"❌ CSV not found at {CSV_PATH}")
        print("Run: python -m src.ingestion.smart_extractor")
        return
    
    # Initialize loader
    loader = DatabaseLoader(DB_PATH)
    
    try:
        # Connect
        loader.connect()
        
        # Create schema
        if not loader.create_schema(schema_path):
            return
        
        # Load data
        if not loader.load_data(CSV_PATH):
            return
        
        # Get stats
        print("\n" + "="*70)
        print("📊 DATABASE STATISTICS")
        print("="*70)
        
        stats = loader.get_stats()
        print(f"\n📊 Total records: {stats['total_records']}")
        print(f"📊 Total circonscriptions: {stats['total_circonscriptions']}")
        print(f"📊 Total winners: {stats['total_winners']}")
        print(f"📊 Total parties: {stats['total_parties']}")
        
        print("\n🏆 Top 5 parties by seats:")
        for party, seats in stats['top_parties']:
            print(f"  {party}: {seats} siège(s)")
        
        # Test views
        loader.test_views()
        
        print("\n" + "="*70)
        print("✅ DATABASE READY!")
        print("="*70)
        print(f"\n📍 Database location: {DB_PATH}")
        
    finally:
        loader.close()

if __name__ == "__main__":
    main()