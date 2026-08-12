"""Project routes with file attachment support."""
import os
import time
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.utils import secure_filename

from app.extensions import db

projects_bp = Blueprint('projects', __name__)


def save_project_file(file, project_id):
    if not file or not file.filename:
        return
    
    raw_filename = file.filename.replace('\\', '/')
    filename_parts = [part.strip() for part in raw_filename.split('/') if part.strip()]
    if not filename_parts:
        return
        
    safe_parts = []
    for part in filename_parts:
        sec = secure_filename(part)
        if not sec:
            sec = f"file_{int(time.time())}"
        safe_parts.append(sec)
        
    rel_folder = os.path.join(*safe_parts[:-1]) if len(safe_parts) > 1 else ''
    safe_name = safe_parts[-1]
    
    project_dir = os.path.join('static', 'uploads', 'projects', str(project_id), rel_folder)
    os.makedirs(project_dir, exist_ok=True)
    
    save_path = os.path.join(project_dir, safe_name)
    file.save(save_path)
    
    relative_url_path = f"uploads/projects/{project_id}/" + ('/'.join(safe_parts))
    file_size = os.path.getsize(save_path) if os.path.exists(save_path) else 0
    ext = os.path.splitext(safe_name)[1].lower().lstrip('.')
    
    display_name = '/'.join(filename_parts)
    
    db.add_project_file(project_id, display_name, relative_url_path, ext, file_size)


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
    files = db.get_project_files(project_id)
    work_items = db.get_work_items(project_id=project_id) if hasattr(db, 'get_work_items') else []
    metrics = db.get_project_dashboard_metrics(project_id) if hasattr(db, 'get_project_dashboard_metrics') else {}
    return render_template('projects/view_project.html', project=project, tasks=tasks, files=files, work_items=work_items, metrics=metrics)


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
            
            # Handle uploaded files from both inputs
            files1 = request.files.getlist('project_files')
            files2 = request.files.getlist('project_folder')
            for f in files1 + files2:
                save_project_file(f, project_id)

            flash('Project updated successfully!', 'success')
            return redirect(url_for('projects.view_project', project_id=project_id))
        except Exception as e:
            flash(f'Error updating project: {str(e)}', 'error')

    files = db.get_project_files(project_id)
    return render_template('projects/edit_project.html', project=project, files=files)


@projects_bp.route('/admin/delete_project_file/<int:file_id>')
def delete_project_file(file_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    file_rec = db.get_project_file(file_id)
    if file_rec:
        project_id = file_rec[1]
        relative_path = file_rec[3]
        full_path = os.path.join('static', relative_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception:
                pass
        db.delete_project_file(file_id)
        flash('File deleted successfully!', 'success')
        return redirect(url_for('projects.edit_project', project_id=project_id))

    flash('File not found.', 'error')
    return redirect(url_for('projects.view_projects'))


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
            project_id = db.add_project(project_data)

            # Handle uploaded files from both inputs
            files1 = request.files.getlist('project_files')
            files2 = request.files.getlist('project_folder')
            for f in files1 + files2:
                save_project_file(f, project_id)

            flash('Project added successfully!', 'success')
            return redirect(url_for('projects.view_project', project_id=project_id))
        except Exception as e:
            flash(f'Error adding project: {str(e)}', 'error')

    return render_template('projects/add_project.html')
