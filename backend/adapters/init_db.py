import os
from adapters.orm import create_tables
from backend.adapters.config import get_postgres_uri
from dotenv import load_dotenv

load_dotenv()


def init_db():
      database_url = get_postgres_uri()

      # Fix incorrect `postgres://` format (SQLAlchemy requires `postgresql+psycopg2://`)
      if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
      print(f"Creating tables in database: {database_url}")
      create_tables(database_url)
      print("Tables created successfully!")


if __name__ == "__main__":
    init_db()
