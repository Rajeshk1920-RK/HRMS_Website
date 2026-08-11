"""Application factory for the HRMS Flask app."""
import os
import logging

from flask import Flask

from app.config import (
    SECRET_KEY, TEMPLATE_DIR, STATIC_DIR,
    UPLOAD_FOLDER, INVOICE_FOLDER, WIKI_CAT_FOLDER, PROFILE_PHOTO_FOLDER,
)
from app.filters import register_filters

# Configure logging (same as the original app.py)
logging.basicConfig(level=logging.DEBUG)


def create_app():
    app = Flask(__name__,
                template_folder=TEMPLATE_DIR,
                static_folder=STATIC_DIR)
    app.secret_key = SECRET_KEY

    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['WIKI_CAT_FOLDER'] = WIKI_CAT_FOLDER
    app.config['PROFILE_PHOTO_FOLDER'] = PROFILE_PHOTO_FOLDER

    # Ensure upload folders exist
    for folder in (UPLOAD_FOLDER, INVOICE_FOLDER, WIKI_CAT_FOLDER, PROFILE_PHOTO_FOLDER):
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Template filters + context processor
    register_filters(app)

    # Blueprints (no url_prefix — URL paths are unchanged)
    from app.routes import all_blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)

    return app


def __getattr__(name):
    if name == 'app':
        app_instance = create_app()
        globals()['app'] = app_instance
        return app_instance
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

