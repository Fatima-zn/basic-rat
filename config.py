import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass 

HOST = "https://server-70ts.onrender.com"

BUFFER_SIZE = 4096
ENCRYPTION_KEY = "vErY_SeCrEt_KeY.57976461314853"
CHUNK_SIZE = 8192

# Database Config
# Format: postgresql://user:password@host:port/database
DATABASE_URL = os.getenv('DATABASE_URL', None)
USE_DATABASE = os.getenv('USE_DATABASE', 'true').lower() == 'true'
