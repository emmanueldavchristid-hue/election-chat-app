"""
Script to explore the PDF structure and understand the data layout.
"""
import pdfplumber
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import PDF_PATH

def explore_pdf_structure():
    """Explore the structure of the PDF to understand the layout."""
    
    print("=" * 70)
    print("📖 EXPLORING PDF STRUCTURE")
    print("=" * 70)
    
    with pdfplumber.open(PDF_PATH) as pdf:
        print(f"\n📄 Total pages: {len(pdf.pages)}")
        
        # Examine first few pages in detail
        for page_num in [1, 2, 3]:
            print(f"\n{'='*70}")
            print(f"📄 PAGE {page_num}")
            print('='*70)
            
            page = pdf.pages[page_num - 1]
            
            # Extract text
            text = page.extract_text()
            print("\n📝 RAW TEXT (first 500 chars):")
            print("-" * 70)
            print(text[:500] if text else "No text found")
            
            # Extract tables
            tables = page.extract_tables()
            print(f"\n📊 TABLES FOUND: {len(tables)}")
            
            for idx, table in enumerate(tables):
                print(f"\n  Table {idx + 1}:")
                print(f"  - Rows: {len(table)}")
                print(f"  - Columns: {len(table[0]) if table else 0}")
                
                if table and len(table) > 0:
                    print(f"\n  First 5 rows:")
                    for row_idx, row in enumerate(table[:5]):
                        print(f"    Row {row_idx}: {row}")
            
            if page_num == 1:
                input("\nPress Enter to continue to next page...")

if __name__ == "__main__":
    if not PDF_PATH.exists():
        print(f"❌ PDF not found at {PDF_PATH}")
        print("Run: python scripts/download_pdf.py")
        sys.exit(1)
    
    explore_pdf_structure()