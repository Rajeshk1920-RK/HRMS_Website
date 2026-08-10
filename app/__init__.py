"""Application factory for the HRMS Flask app."""
import os
import logging

from flask import Flask

from app.config import (
    SECRET_KEY, TEMPLATE_DIR, STATIC_DIR,
    UPLOAD_FOLDER, INVOICE_FOLDER, WIKI_CAT_FOLDER,
)
from app.filters import register_filters

# Configure logging (same as the original app.py)
logging.basicConfig(level=logging.DEBUG)


def create_app():
    from app.config import PERSISTENT_DATA_DIR

    app = Flask(__name__,
                template_folder=TEMPLATE_DIR,
                static_folder=STATIC_DIR)
    app.secret_key = SECRET_KEY

    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['WIKI_CAT_FOLDER'] = WIKI_CAT_FOLDER

    # Ensure upload folders exist (and handle symlinking if PERSISTENT_DATA_DIR is configured)
    if PERSISTENT_DATA_DIR:
        import shutil
        for folder_path, folder_name in [
            (UPLOAD_FOLDER, 'bngImg'),
            (INVOICE_FOLDER, 'invoices'),
            (WIKI_CAT_FOLDER, 'wikiCatImg')
        ]:
            persistent_folder = os.path.join(PERSISTENT_DATA_DIR, folder_name)
            os.makedirs(persistent_folder, exist_ok=True)
            
            # If the static subdirectory is not already a symlink, link it to the persistent folder
            if not os.path.islink(folder_path):
                # If there are existing files, migrate them to the persistent storage
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    for item in os.listdir(folder_path):
                        src = os.path.join(folder_path, item)
                        dst = os.path.join(persistent_folder, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src, dst)
                    shutil.rmtree(folder_path)
                
                # Create the symlink pointing to the persistent directory
                os.symlink(persistent_folder, folder_path)
    else:
        for folder in (UPLOAD_FOLDER, INVOICE_FOLDER, WIKI_CAT_FOLDER):
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

