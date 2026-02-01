"""
Script to download the election results PDF from CEI website.
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def download_pdf():
    """Download the election results PDF."""
    
    # Get PDF URL from environment
    pdf_url = os.getenv('PDF_URL')
    if not pdf_url:
        print("❌ Error: PDF_URL not found in .env file")
        sys.exit(1)
    
    # Create data/raw directory if it doesn't exist
    raw_data_dir = project_root / 'data' / 'raw'
    raw_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Output file path
    output_path = raw_data_dir / 'EDAN_2025_RESULTAT_NATIONAL_DETAILS.pdf'
    
    # Check if file already exists
    if output_path.exists():
        print(f"📄 PDF already exists at: {output_path}")
        response = input("Do you want to re-download? (y/n): ")
        if response.lower() != 'y':
            print("✅ Using existing PDF file")
            return
    
    print(f"📥 Downloading PDF from: {pdf_url}")
    print("⏳ This may take a few moments...")
    
    try:
        # Download with progress indication
        response = requests.get(pdf_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Get total file size
        total_size = int(response.headers.get('content-length', 0))
        
        # Write to file
        with open(output_path, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress = (downloaded / total_size) * 100
                    print(f"\r⏳ Progress: {progress:.1f}%", end='', flush=True)
        
        print(f"\n✅ PDF downloaded successfully!")
        print(f"📍 Location: {output_path}")
        print(f"📊 Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error downloading PDF: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("📥 Election Results PDF Downloader")
    print("=" * 60)
    download_pdf()
    print("=" * 60)