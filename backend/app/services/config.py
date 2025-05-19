import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Database configuration
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "168.220.245.22"),
    "database": os.getenv("DB_NAME", "nembutest"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "Cloud@2025"),
    "port": os.getenv("DB_PORT", "5432")
}

# Construct the database URL with proper URL encoding
from urllib.parse import quote_plus

password = quote_plus(DATABASE_CONFIG['password'])
DATABASE_URL = f"postgresql://{DATABASE_CONFIG['user']}:{password}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
logger = logging.getLogger(__name__)
logger.info(" Database URL configured for PostgreSQL")
