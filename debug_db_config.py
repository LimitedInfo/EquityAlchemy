import os
from dotenv import load_dotenv

load_dotenv()

print("=== Environment Variables ===")
print(f"DB_USER: {os.getenv('DB_USER')}")
print(f"DB_PASSWORD: {os.getenv('DB_PASSWORD')}")
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_PORT: {os.getenv('DB_PORT')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")

db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
database_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

print(f"\n=== Constructed Database URL ===")
print(f"Raw: {database_url}")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)

print(f"Final: {database_url}")

print("\n=== Testing Connection ===")
try:
    from sqlalchemy import create_engine
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("✅ Connection successful!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
