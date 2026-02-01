import os

# Try to load dotenv if available, but don't crash if not
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available in compiled exe, use hardcoded values

HOST = "https://server-70ts.onrender.com"

BUFFER_SIZE = 4096
ENCRYPTION_KEY = "vErY_SeCrEt_KeY.57976461314853"
CHUNK_SIZE = 8192

# Database Configuration (Supabase/PostgreSQL)
# Format: postgresql://user:password@host:port/database
# Exemple Supabase: postgresql://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
DATABASE_URL = os.getenv('DATABASE_URL', None)
USE_DATABASE = os.getenv('USE_DATABASE', 'true').lower() == 'true'
