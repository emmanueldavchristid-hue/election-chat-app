"""
Configuration management for the election chat application.
UPDATED: Support pour Ollama, Anthropic et OpenAI/OpenRouter
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SCHEMA_DIR = DATA_DIR / "schema"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

# PDF Configuration
PDF_URL = os.getenv('PDF_URL', 'https://www.cei.ci/wp-content/uploads/2025/12/EDAN_2025_RESULTAT_NATIONAL_DETAILS.pdf')
PDF_PATH = RAW_DATA_DIR / 'EDAN_2025_RESULTAT_NATIONAL_DETAILS.pdf'

# Database Configuration
DB_PATH = Path(os.getenv('DB_PATH', str(PROCESSED_DATA_DIR / 'elections.duckdb')))
CSV_PATH = PROCESSED_DATA_DIR / 'elections.csv'
PARQUET_PATH = PROCESSED_DATA_DIR / 'elections.parquet'

# ========================================
# LLM Configuration
# ========================================
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')  # 'ollama' | 'anthropic' | 'openai'

# Ollama Configuration
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')

# OpenAI / OpenRouter Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')  # Pour OpenRouter: https://openrouter.ai/api/v1

# Query Safety Configuration
MAX_QUERY_RESULTS = int(os.getenv('MAX_QUERY_RESULTS', 1000))
QUERY_TIMEOUT_SECONDS = int(os.getenv('QUERY_TIMEOUT_SECONDS', 30))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Application Configuration
APP_TITLE = os.getenv('APP_TITLE', 'Election Results Chat')
APP_PORT = int(os.getenv('APP_PORT', 8501))

# SQL Security - Forbidden keywords
FORBIDDEN_SQL_KEYWORDS = [
    'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
    'CREATE', 'TRUNCATE', 'REPLACE', 'EXEC', 'EXECUTE'
]

# Allowed SQL keywords
ALLOWED_SQL_KEYWORDS = [
    'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY',
    'LIMIT', 'JOIN', 'HAVING', 'AS', 'COUNT', 'SUM',
    'AVG', 'MAX', 'MIN', 'DISTINCT'
]

def validate_config() -> bool:
    """Validate that all required configuration is present."""
    errors = []
    
    # Vérifier le provider LLM
    if LLM_PROVIDER not in ['ollama', 'anthropic', 'openai']:
        errors.append(f"LLM_PROVIDER doit être 'ollama', 'anthropic' ou 'openai', pas '{LLM_PROVIDER}'")
    
    # Vérifier la config selon le provider
    if LLM_PROVIDER == 'anthropic' and not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY manquante pour le provider 'anthropic'")
    
    if LLM_PROVIDER == 'openai' and not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY manquante pour le provider 'openai'")
    
    if LLM_PROVIDER == 'ollama':
        print(f"ℹ️  Provider: Ollama ({OLLAMA_MODEL})")
        print(f"ℹ️  URL: {OLLAMA_BASE_URL}")
    elif LLM_PROVIDER == 'openai':
        if OPENAI_BASE_URL and 'openrouter' in OPENAI_BASE_URL:
            print(f"ℹ️  Provider: OpenRouter ({OPENAI_MODEL})")
        else:
            print(f"ℹ️  Provider: OpenAI ({OPENAI_MODEL})")
    else:
        print(f"ℹ️  Provider: Anthropic ({ANTHROPIC_MODEL})")
    
    if not PDF_PATH.exists():
        errors.append(f"PDF not found at {PDF_PATH}. Run scripts/download_pdf.py first.")
    
    if errors:
        for error in errors:
            print(f"❌ Configuration Error: {error}")
        return False
    
    return True

def get_config_info() -> dict:
    """Get current configuration information."""
    return {
        'project_root': str(PROJECT_ROOT),
        'pdf_path': str(PDF_PATH),
        'pdf_exists': PDF_PATH.exists(),
        'db_path': str(DB_PATH),
        'llm_provider': LLM_PROVIDER,
        'ollama_model': OLLAMA_MODEL if LLM_PROVIDER == 'ollama' else None,
        'anthropic_model': ANTHROPIC_MODEL if LLM_PROVIDER == 'anthropic' else None,
        'openai_model': OPENAI_MODEL if LLM_PROVIDER == 'openai' else None,
        'api_key_set': bool(ANTHROPIC_API_KEY) if LLM_PROVIDER == 'anthropic' else bool(OPENAI_API_KEY) if LLM_PROVIDER == 'openai' else None,
        'max_query_results': MAX_QUERY_RESULTS,
        'query_timeout': QUERY_TIMEOUT_SECONDS,
    }