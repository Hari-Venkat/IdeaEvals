import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ADDITIONAL_FILES_DIR = DATA_DIR / "additional_files"
SCHEMA_FILE = BASE_DIR / "config" / "schema.json"

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', 5432))
}

# Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')

# Processing settings
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 8))  # Number of ideas to process in parallel
MAX_FILE_WORKERS = int(os.getenv('MAX_FILE_WORKERS', 3))  # Number of files to process in parallel per idea

MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
TIMEOUT_SECONDS = int(os.getenv('TIMEOUT_SECONDS', 120))

# File settings
SUPPORTED_EXTENSIONS = ['.pdf', '.pptx', '.docx', '.mp4', '.mov', '.jpg', '.jpeg', '.png', '.webp']
MAX_FILE_SIZE_MB = 50

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = BASE_DIR / "pipeline.log"
