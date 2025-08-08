import os
from adapters.orm import create_tables
from adapters.config import get_postgres_uri
from dotenv import load_dotenv

load_dotenv()


def init_db():
      database_url = get_postgres_uri()

      # Fix database URL format (SQLAlchemy requires `postgresql+psycopg://`)
      if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
      elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
      print(f"Creating tables in database: {database_url}")
      create_tables(database_url)
      print("Tables created successfully!")


if __name__ == "__main__":
    init_db()
