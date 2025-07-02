import os
from sqlalchemy import create_engine, text
from adapters.config import get_postgres_uri
from dotenv import load_dotenv

load_dotenv()

def migrate_add_missing_columns():
    database_url = get_postgres_uri()

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)

    print(f"Connecting to database: {database_url}")
    engine = create_engine(database_url)

    with engine.connect() as conn:
        try:
            print("Checking if 'has_more_than_one_continuous_period' column exists...")
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'combined_financial_statements'
                AND column_name = 'has_more_than_one_continuous_period'
            """))

            if not result.fetchone():
                print("Adding 'has_more_than_one_continuous_period' column...")
                conn.execute(text("""
                    ALTER TABLE combined_financial_statements
                    ADD COLUMN has_more_than_one_continuous_period BOOLEAN NULL
                """))
                conn.commit()
                print("✓ Added 'has_more_than_one_continuous_period' column")
            else:
                print("✓ 'has_more_than_one_continuous_period' column already exists")

        except Exception as e:
            print(f"Error adding 'has_more_than_one_continuous_period' column: {e}")
            conn.rollback()

        try:
            print("Checking if 'sec_filings_url' column exists...")
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'combined_financial_statements'
                AND column_name = 'sec_filings_url'
            """))

            if not result.fetchone():
                print("Adding 'sec_filings_url' column...")
                conn.execute(text("""
                    ALTER TABLE combined_financial_statements
                    ADD COLUMN sec_filings_url VARCHAR NULL
                """))
                conn.commit()
                print("✓ Added 'sec_filings_url' column")
            else:
                print("✓ 'sec_filings_url' column already exists")

        except Exception as e:
            print(f"Error adding 'sec_filings_url' column: {e}")
            conn.rollback()

    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_add_missing_columns()
