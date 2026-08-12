"""Project routes (moved verbatim from app.py)."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.extensions import db

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/admin/view_projects')
def view_projects():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    projects = db.get_projects()
    return render_template('projects/view_projects.html', projects=projects)

@projects_bp.route('/admin/view_project/<int:project_id>')
def view_project(project_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    project = db.get_project(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects.view_projects'))

    tasks = db.get_tasks_by_project(project_id)
    work_items = db.get_work_items(project_id=project_id)
    metrics = db.get_project_dashboard_metrics(project_id)
    return render_template('projects/view_project.html', project=project, tasks=tasks, work_items=work_items, metrics=metrics)

@projects_bp.route('/admin/edit_project/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    project = db.get_project(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects.view_projects'))

    if request.method == 'POST':
        project_data = {
            'project_name': request.form['project_name'],
            'priority': request.form['priority'],
            'project_desc': request.form['project_desc'],
            'project_status': request.form['project_status'],
            'start_date': request.form['start_date'],
            'end_date': request.form['end_date']
        }

        try:
            db.update_project(project_id, project_data)
            flash('Project updated successfully!', 'success')
            return redirect(url_for('projects.view_projects'))
        except Exception as e:
            flash('Error updating project.', 'error')

    return render_template('projects/edit_project.html', project=project)

@projects_bp.route('/admin/delete_project/<int:project_id>')
def delete_project(project_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    try:
        db.delete_project(project_id)
        flash('Project deleted successfully!', 'success')
    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('projects.view_projects'))

@projects_bp.route('/admin/add_project', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        project_data = {
            'project_name': request.form['project_name'],
            'priority': request.form['priority'],
            'project_desc': request.form['project_desc'],
            'project_status': request.form['project_status'],
            'start_date': request.form['start_date'],
            'end_date': request.form['end_date']
        }

        try:
            db.add_project(project_data)
            flash('Project added successfully!', 'success')
            return redirect(url_for('projects.view_projects'))
        except Exception as e:
            flash('Error adding project.', 'error')

    return render_template('projects/add_project.html')
