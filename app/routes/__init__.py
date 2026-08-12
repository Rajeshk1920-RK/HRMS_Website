"""Route blueprints package."""
from app.routes.auth import auth_bp
from app.routes.employees import employees_bp
from app.routes.projects import projects_bp
from app.routes.tasks import tasks_bp
from app.routes.leave import leave_bp
from app.routes.expenses import expenses_bp
from app.routes.wiki import wiki_bp
from app.routes.careers import careers_bp
from app.routes.assets import assets_bp
from app.routes.work_items import work_items_bp

all_blueprints = (
    auth_bp,
    employees_bp,
    projects_bp,
    tasks_bp,
    leave_bp,
    expenses_bp,
    wiki_bp,
    careers_bp,
    assets_bp,
    work_items_bp,
)
