import os
from dotenv import load_dotenv

load_dotenv()


def get_postgres_uri() -> str:
    if os.environ.get("FLY_APP_NAME"):
        host = os.environ.get("DATABASE_HOST", "twilight-river-6306.flycast")
        port = os.environ.get("DATABASE_PORT", "5432")
        password = os.environ.get("DATABASE_PASSWORD", os.environ.get("OPERATOR_PASSWORD", ""))
        user = os.environ.get("DATABASE_USER", "postgres")
        db_name = os.environ.get("DATABASE_NAME", "postgres")
        print(f"postgresql://{user}:{password}@{host}:{port}/{db_name}")
        return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    else:
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        password = os.environ.get("DB_PASSWORD", "postgres")
        user = os.environ.get("DB_USER", "postgres")
        db_name = os.environ.get("DB_NAME", "combined_financial_statements")
        print(f"postgresql://{user}:{password}@{host}:{port}/{db_name}")
        return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_api_url() -> str:
    host = os.environ.get("API_HOST", "localhost")
    port = os.environ.get("API_PORT", "8000")
    return f"http://{host}:{port}"
