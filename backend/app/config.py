# backend/app/config.py
import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

DB_NAME = os.getenv("DB_NAME", "geo_ads")
DB_USER = os.getenv("DB_USER", "geo_ads_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "geo_ads_password")

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    return conn
