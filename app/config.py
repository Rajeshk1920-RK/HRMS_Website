"""Central configuration for the HRMS application.

All filesystem paths are anchored to the project root (BASE_DIR) so the
application behaves identically regardless of the current working directory.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Project root (one level above the app/ package)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Flask
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Template / static locations (kept at project root)
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Check if a persistent data directory is mounted (Render environment variable)
PERSISTENT_DATA_DIR = os.getenv('PERSISTENT_DATA_DIR')

if PERSISTENT_DATA_DIR:
    # Ensure the persistent directory exists
    os.makedirs(PERSISTENT_DATA_DIR, exist_ok=True)

# PostgreSQL connection
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_PRIVATE_URL')

if DATABASE_URL:
    DB_DSN = DATABASE_URL
else:
    # Support both standard Postgres variables (PGHOST, etc.) and custom ones (PG_HOST, etc.)
    PG_HOST = os.getenv('PGHOST') or os.getenv('PG_HOST') or 'localhost'
    PG_PORT = os.getenv('PGPORT') or os.getenv('PG_PORT') or '5432'
    PG_DBNAME = os.getenv('PGDATABASE') or os.getenv('PG_DBNAME') or os.getenv('PG_DATABASE') or 'project_tracking'
    PG_USER = os.getenv('PGUSER') or os.getenv('PG_USER') or 'postgres'
    PG_PASSWORD = os.getenv('PGPASSWORD') or os.getenv('PG_PASSWORD') or ''
    DB_DSN = f"host={PG_HOST} port={PG_PORT} dbname={PG_DBNAME} user={PG_USER} password={PG_PASSWORD}"


# Upload folders
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'bngImg')
INVOICE_FOLDER = os.path.join(BASE_DIR, 'static', 'invoices')
WIKI_CAT_FOLDER = os.path.join(BASE_DIR, 'static', 'wikiCatImg')

# Excel template used for expense reports
EXPENSE_TEMPLATE_PATH = os.path.join(BASE_DIR, 'Expense-Details.xlsx')
