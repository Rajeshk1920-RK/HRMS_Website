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
PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = os.getenv('PG_PORT', '5432')
PG_DBNAME = os.getenv('PG_DBNAME', 'project_tracking')
PG_USER = os.getenv('PG_USER', 'postgres')
PG_PASSWORD = os.getenv('PG_PASSWORD', '')

DB_DSN = f"host={PG_HOST} port={PG_PORT} dbname={PG_DBNAME} user={PG_USER} password={PG_PASSWORD}"

# Upload folders
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'bngImg')
INVOICE_FOLDER = os.path.join(BASE_DIR, 'static', 'invoices')
WIKI_CAT_FOLDER = os.path.join(BASE_DIR, 'static', 'wikiCatImg')

# Excel template used for expense reports
EXPENSE_TEMPLATE_PATH = os.path.join(BASE_DIR, 'Expense-Details.xlsx')
