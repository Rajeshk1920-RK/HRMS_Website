"""Composed Database class.

The original monolithic Database class from database.py is split into
feature mixins; this class recombines them so callers keep using a single
`Database` object exactly as before. Method bodies are unchanged.
"""
from app.models.base import DatabaseBase
from app.models.auth import AuthMixin
from app.models.employees import EmployeeMixin
from app.models.projects import ProjectMixin
from app.models.tasks import TaskMixin
from app.models.leave import LeaveMixin
from app.models.expenses import ExpenseMixin
from app.models.wiki import WikiMixin
from app.models.admin import AdminMixin
from app.models.work_items import WorkItemMixin


class Database(AuthMixin, EmployeeMixin, ProjectMixin, TaskMixin,
               LeaveMixin, ExpenseMixin, WikiMixin, AdminMixin,
               WorkItemMixin, DatabaseBase):
    pass
