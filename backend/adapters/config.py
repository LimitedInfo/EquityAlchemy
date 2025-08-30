import os
from dotenv import load_dotenv

load_dotenv()


def get_postgres_uri() -> str:
    if os.environ.get("ENV") == 'LOCAL':
        db_url = os.environ.get("DATABASE_URL_LOCAL")
    else:
        db_url = os.environ.get("DATABASE_URL")
    
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    return db_url




def get_api_url() -> str:
    host = os.environ.get("API_HOST", "localhost")
    port = os.environ.get("API_PORT", "8000")
    return f"http://{host}:{port}"
