"""Shared application singletons.

The Database instance and the raw psycopg2 connection helper live here so
that route modules can import them without circular imports.
"""
import psycopg2
import psycopg2.extras

from app.config import DB_DSN
from app.models import Database

# Single shared Database instance (created once at import time)
db = Database(DB_DSN)


def get_db_connection():
    conn = psycopg2.connect(DB_DSN, connection_factory=psycopg2.extras.RealDictConnection)
    return conn
