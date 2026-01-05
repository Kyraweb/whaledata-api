import os
import psycopg2

DB_USER = os.getenv("DB_USER", "whaledata_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")
DB_HOST = os.getenv("DB_HOST", "whaledata-db")  # Coolify service name
DB_NAME = os.getenv("DB_NAME", "whaledata")
DB_PORT = os.getenv("DB_PORT", 5432)

def get_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn
