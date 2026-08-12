"""Project management routes."""
import os
import time
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
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

# ========== ADMIN PROJECT DASHBOARD ==========
@projects_bp.route('/admin/project_dashboard')
def project_dashboard():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    return redirect(url_for('employees.admin_dashboard'))

# ========== ALL PROJECTS ==========
@projects_bp.route('/admin/view_projects')
def view_projects():
    if 'user_id' not in session or session['emp_type'] not in ['admin', 'emp', 'tester']:
        return redirect(url_for('auth.login'))

    search = request.args.get('search', '').strip()
    domain = request.args.get('domain', '').strip()
    status = request.args.get('status', '').strip()
    priority = request.args.get('priority', '').strip()
    
    projects = db.get_projects_filtered(
        search=search or None,
        domain=domain or None,
        status=status or None,
        priority=priority or None,
        include_archived=False
    )
    
    # Add team size and health metrics
    processed_projects = []
    for p in projects:
        members = db.get_project_members(p[0])
        health = db.get_project_health(p[0])
        processed_projects.append(list(p) + [len(members), health])

    employees = db.get_employees()
    return render_template('projects/view_projects.html',
                           projects=processed_projects,
                           employees=employees,
                           search=search,
                           selected_domain=domain,
                           selected_status=status,
                           selected_priority=priority)

# ========== ADD PROJECT ==========
@projects_bp.route('/admin/add_project', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        project_data = {
            'project_name': request.form['project_name'].strip(),
            'project_code': request.form['project_code'].strip(),
            'project_type': request.form['project_type'],
            'priority': request.form['priority'],
            'project_status': request.form['project_status'],
            'start_date': request.form['start_date'],
            'end_date': request.form['end_date'],
            'github_repo': request.form.get('github_repo', '').strip(),
            'project_manager_id': request.form.get('project_manager_id'),
            'team_lead_id': request.form.get('team_lead_id'),
            'created_by': session['user_id']
        }

        if not project_data['project_name'] or not project_data['project_code']:
            flash('Error: Project name and unique code are required.', 'error')
        else:
            try:
                project_id = db.add_project(project_data)

                # Auto assign project manager and team lead to project members
                if project_data['project_manager_id']:
                    db.add_project_member(project_id, int(project_data['project_manager_id']), 'Project Manager', session['user_id'])
                if project_data['team_lead_id']:
                    db.add_project_member(project_id, int(project_data['team_lead_id']), 'Team Lead', session['user_id'])

                # Handle files
                files1 = request.files.getlist('project_files')
                files2 = request.files.getlist('project_folder')
                for f in files1 + files2:
                    save_project_file(f, project_id)

                flash('Project created successfully!', 'success')
                return redirect(url_for('projects.view_project', project_id=project_id))
            except Exception as e:
                flash(f'Error adding project: {str(e)}', 'error')

    employees = db.get_employees()
    return render_template('projects/add_project.html', employees=employees)

# ========== EDIT PROJECT ==========
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
            'project_name': request.form['project_name'].strip(),
            'project_code': request.form['project_code'].strip(),
            'project_type': request.form['project_type'],
            'priority': request.form['priority'],
            'project_status': request.form['project_status'],
            'start_date': request.form['start_date'],
            'end_date': request.form['end_date'],
            'github_repo': request.form.get('github_repo', '').strip(),
            'project_manager_id': request.form.get('project_manager_id'),
            'team_lead_id': request.form.get('team_lead_id'),
            'updated_by': session['user_id']
        }

        try:
            db.update_project(project_id, project_data)

            # Keep members sync
            if project_data['project_manager_id']:
                db.add_project_member(project_id, int(project_data['project_manager_id']), 'Project Manager', session['user_id'])
            if project_data['team_lead_id']:
                db.add_project_member(project_id, int(project_data['team_lead_id']), 'Team Lead', session['user_id'])

            # Handle files
            files1 = request.files.getlist('project_files')
            files2 = request.files.getlist('project_folder')
            for f in files1 + files2:
                save_project_file(f, project_id)

            flash('Project updated successfully!', 'success')
            return redirect(url_for('projects.view_project', project_id=project_id))
        except Exception as e:
            flash(f'Error updating project: {str(e)}', 'error')

    employees = db.get_employees()
    files = db.get_project_files(project_id)

    return render_template('projects/edit_project.html', project=project, employees=employees, files=files)

# ========== ARCHIVE PROJECT ==========
@projects_bp.route('/admin/archive_project/<int:project_id>')
def archive_project(project_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    try:
        db.archive_project(project_id, user_id=session['user_id'])
        flash('Project archived successfully!', 'success')
    except Exception as e:
        flash(f'Error archiving project: {str(e)}', 'error')

    return redirect(url_for('projects.view_projects'))

# ========== PROJECT DETAILS (TABBED) ==========
@projects_bp.route('/admin/view_project/<int:project_id>')
def view_project(project_id):
    if 'user_id' not in session or session['emp_type'] not in ['admin', 'emp', 'tester']:
        return redirect(url_for('auth.login'))

    project = db.get_project(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects.view_projects'))

    active_tab = request.args.get('tab', 'overview')
    
    tasks = db.get_tasks_by_project(project_id)
    files = db.get_project_files(project_id)
    members = db.get_project_members(project_id)
    modules = db.get_project_modules(project_id)
    activity = db.get_project_activity(project_id)
    qa_history = db.get_qa_history(project_id=project_id)
    health = db.get_project_health(project_id)

    # Compute Statistics for overview tab
    stats = {
        'total': len(tasks),
        'todo': len([t for t in tasks if t[5] == 'pending']),
        'in_progress': len([t for t in tasks if t[5] == 'in_progress']),
        'in_review': len([t for t in tasks if t[5] == 'in_review']),
        'qa': len([t for t in tasks if t[5] == 'qa_testing']),
        'completed': len([t for t in tasks if t[5] == 'completed']),
        'blocked': len([t for t in tasks if t[5] == 'blocked']),
    }

    employees = db.get_employees()

    return render_template('projects/view_project.html',
                           project=project,
                           tasks=tasks,
                           files=files,
                           members=members,
                           modules=modules,
                           activity=activity,
                           qa_history=qa_history,
                           health=health,
                           stats=stats,
                           active_tab=active_tab,
                           employees=employees)

# ========== AJAX API ENDPOINTS ==========
@projects_bp.route('/api/projects/<int:project_id>/members')
def api_project_members(project_id):
    members = db.get_project_members(project_id)
    data = []
    for m in members:
        data.append({
            'employee_id': m[2],
            'first_name': m[6],
            'last_name': m[7],
            'email': m[8]
        })
    return jsonify(data)

@projects_bp.route('/api/projects/<int:project_id>/modules')
def api_project_modules(project_id):
    modules = db.get_project_modules(project_id)
    data = []
    for m in modules:
        data.append({
            'module_id': m[0],
            'name': m[2],
            'description': m[3]
        })
    return jsonify(data)

@projects_bp.route('/api/projects/<int:project_id>/my_tasks')
def api_project_my_tasks(project_id):
    if 'user_id' not in session:
        return jsonify([])
    tasks = db.get_tasks_by_employee(session['user_id'])
    data = []
    for t in tasks:
        if t[2] == project_id:
            data.append({
                'task_id': t[0],
                'title': t[7] or t[1]
            })
    return jsonify(data)

# ========== MEMBERS MANAGEMENT ==========
@projects_bp.route('/admin/project/<int:project_id>/add_member', methods=['POST'])
def add_member(project_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    employee_id = int(request.form['employee_id'])
    role = request.form['project_role'].strip()

    if not employee_id or not role:
        flash('Employee and Role are required.', 'error')
    else:
        try:
            db.add_project_member(project_id, employee_id, role, session['user_id'])
            flash('Team member added successfully.', 'success')
        except Exception as e:
            flash(f'Error adding team member: {str(e)}', 'error')

    return redirect(url_for('projects.view_project', project_id=project_id, tab='team'))

@projects_bp.route('/admin/project/<int:project_id>/remove_member/<int:employee_id>', methods=['POST'])
def remove_member(project_id, employee_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    try:
        db.remove_project_member(project_id, employee_id, session['user_id'])
        flash('Team member removed successfully.', 'success')
    except Exception as e:
        flash(f'Error removing member: {str(e)}', 'error')

    return redirect(url_for('projects.view_project', project_id=project_id, tab='team'))

@projects_bp.route('/admin/project/<int:project_id>/change_member_role/<int:employee_id>', methods=['POST'])
def change_member_role(project_id, employee_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    role = request.form['project_role'].strip()
    if not role:
        flash('Role is required.', 'error')
    else:
        try:
            db.update_project_member_role(project_id, employee_id, role, session['user_id'])
            flash('Member role updated successfully.', 'success')
        except Exception as e:
            flash(f'Error updating role: {str(e)}', 'error')

    return redirect(url_for('projects.view_project', project_id=project_id, tab='team'))

# ========== MODULES MANAGEMENT ==========
@projects_bp.route('/admin/project/<int:project_id>/add_module', methods=['POST'])
def add_module(project_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    name = request.form['name'].strip()
    description = request.form.get('description', '').strip()
    lead_id = request.form.get('module_lead_id')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    if not name:
        flash('Module name is required.', 'error')
    else:
        try:
            db.add_project_module(project_id, name, description, int(lead_id) if lead_id else None, start_date, end_date, session['user_id'])
            flash('Module added successfully.', 'success')
        except Exception as e:
            flash(f'Error adding module: {str(e)}', 'error')

    return redirect(url_for('projects.view_project', project_id=project_id, tab='modules'))

@projects_bp.route('/admin/project/<int:project_id>/edit_module/<int:module_id>', methods=['POST'])
def edit_module(project_id, module_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    name = request.form['name'].strip()
    description = request.form.get('description', '').strip()
    lead_id = request.form.get('module_lead_id')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    status = request.form.get('status', 'Active')

    if not name:
        flash('Module name is required.', 'error')
    else:
        try:
            db.update_project_module(module_id, name, description, int(lead_id) if lead_id else None, start_date, end_date, status, session['user_id'])
            flash('Module updated successfully.', 'success')
        except Exception as e:
            flash(f'Error editing module: {str(e)}', 'error')

    return redirect(url_for('projects.view_project', project_id=project_id, tab='modules'))

@projects_bp.route('/admin/project/<int:project_id>/archive_module/<int:module_id>', methods=['POST'])
def archive_module(project_id, module_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    try:
        db.archive_project_module(module_id, session['user_id'])
        flash('Module archived successfully.', 'success')
    except Exception as e:
        flash(f'Error archiving module: {str(e)}', 'error')

    return redirect(url_for('projects.view_project', project_id=project_id, tab='modules'))

# ========== QA TESTING WORKSPACE ==========
@projects_bp.route('/admin/qa_testing')
@projects_bp.route('/admin/qa_testing_queue')
def qa_testing_queue():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    queue = db.get_qa_queue()
    history = db.get_qa_history()
    return render_template('projects/qa_testing_queue.html', queue=queue, history=history)

@projects_bp.route('/admin/perform_qa_test/<int:task_id>', methods=['GET', 'POST'])
def perform_qa_test(task_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    task = db.get_task(task_id)
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('projects.qa_testing_queue'))

    if request.method == 'POST':
        result = request.form['result'] # PASS or FAIL
        expected_result = request.form.get('expected_result', '').strip()
        actual_result = request.form.get('actual_result', '').strip()
        comments = request.form.get('comments', '').strip()

        if result not in ['PASS', 'FAIL']:
            flash('Invalid result value.', 'error')
        else:
            try:
                qa_data = {
                    'task_id': task_id,
                    'tester_id': session['user_id'],
                    'result': result,
                    'expected_result': expected_result,
                    'actual_result': actual_result,
                    'comments': comments
                }
                db.submit_qa_test(qa_data)
                flash('QA verification test logged successfully.', 'success')
                return redirect(url_for('projects.qa_testing_queue'))
            except Exception as e:
                flash(f'Error submitting test: {str(e)}', 'error')

    return render_template('projects/perform_qa.html', task=task)

# ========== PROJECT & EMPLOYEE REPORTS ==========
@projects_bp.route('/admin/projects/reports')
@projects_bp.route('/admin/project_reports')
def project_reports():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    selected_project = request.args.get('project_id', type=int)
    selected_employee = request.args.get('employee_id', type=int)
    
    projects = db.get_projects()
    employees = db.get_employees()

    report_data = None
    if selected_project:
        project_details = db.get_project(selected_project)
        tasks = db.get_tasks_by_project(selected_project)
        members = db.get_project_members(selected_project)
        modules = db.get_project_modules(selected_project)
        health = db.get_project_health(selected_project)
        qa_history = db.get_qa_history(project_id=selected_project)
        
        report_data = {
            'type': 'project',
            'details': project_details,
            'tasks': tasks,
            'members': members,
            'modules': modules,
            'health': health,
            'qa_history': qa_history
        }
    elif selected_employee:
        emp_details = next((e for e in employees if e[0] == selected_employee), None)
        emp_tasks = db.get_tasks_by_employee(selected_employee)
        emp_reports = db.get_work_reports_by_employee(selected_employee)
        
        report_data = {
            'type': 'employee',
            'details': emp_details,
            'tasks': emp_tasks,
            'reports': emp_reports
        }

    return render_template('projects/project_reports.html',
                           projects=projects,
                           employees=employees,
                           selected_project=selected_project,
                           selected_employee=selected_employee,
                           report_data=report_data)

# ========== ADMIN WORK REPORTS MONITORING ==========
@projects_bp.route('/admin/work_reports')
def admin_work_reports():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    selected_project = request.args.get('project_id', type=int)
    selected_employee = request.args.get('employee_id', type=int)
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    reports = db.get_all_work_reports(
        employee_id=selected_employee or None,
        project_id=selected_project or None,
        start_date=start_date or None,
        end_date=end_date or None
    )

    projects = db.get_projects()
    employees = db.get_employees()

    return render_template('projects/admin_work_reports.html',
                           reports=reports,
                           projects=projects,
                           employees=employees,
                           selected_project=selected_project,
                           selected_employee=selected_employee,
                           start_date=start_date,
                           end_date=end_date)

@projects_bp.route('/admin/work_reports/lock/<int:report_id>', methods=['POST'])
def lock_work_report(report_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    status = request.form.get('status', 'approved')
    try:
        db.lock_work_report(report_id, status=status, user_id=session['user_id'])
        flash(f'Work report status updated to {status} (locked).', 'success')
    except Exception as e:
        flash(f'Error locking work report: {str(e)}', 'error')

    return redirect(url_for('projects.admin_work_reports'))

# =========================================================================
# ========== EMPLOYEE CAPABILITIES ==========
# =========================================================================

# ========== MY PROJECTS ==========
@projects_bp.route('/employee/my_projects')
def my_projects():
    if 'user_id' not in session or session['emp_type'] not in ['emp', 'tester']:
        return redirect(url_for('auth.login'))

    my_projects = db.get_projects_by_employee(session['user_id'])
    
    # Calculate task metrics for each project
    projects_with_counts = []
    for p in my_projects:
        tasks = db.get_tasks_by_project(p[0])
        my_tasks_count = len([t for t in tasks if t[3] == session['user_id']])
        projects_with_counts.append(list(p) + [my_tasks_count])

    return render_template('projects/my_projects.html', projects=projects_with_counts)

# ========== MY PROJECT DETAILS ==========
@projects_bp.route('/employee/my_project_details/<int:project_id>')
def my_project_details(project_id):
    if 'user_id' not in session or session['emp_type'] not in ['emp', 'tester']:
        return redirect(url_for('auth.login'))

    # Verify membership
    members = db.get_project_members(project_id)
    member_ids = [m[2] for m in members]
    if session['user_id'] not in member_ids:
        flash('Access denied: You are not assigned to this project.', 'error')
        return redirect(url_for('projects.my_projects'))

    project = db.get_project(project_id)
    active_tab = request.args.get('tab', 'overview')
    
    tasks = db.get_tasks_by_project(project_id)
    my_tasks = [t for t in tasks if t[3] == session['user_id']]
    activity = db.get_project_activity(project_id)

    return render_template('projects/my_project_details.html',
                           project=project,
                           my_tasks=my_tasks,
                           members=members,
                           activity=activity,
                           active_tab=active_tab)

# ========== MY TASKS ==========
@projects_bp.route('/employee/my_tasks')
def my_tasks():
    if 'user_id' not in session or session['emp_type'] not in ['emp', 'tester']:
        return redirect(url_for('auth.login'))

    status_filter = request.args.get('status', 'all')
    project_id = request.args.get('project_id', type=int)
    active_tab = request.args.get('tab', 'tasks')

    tasks = db.get_tasks_by_employee(session['user_id'])
    
    # Filter list
    if status_filter != 'all':
        tasks = [t for t in tasks if t[3] == status_filter]
    if project_id:
        tasks = [t for t in tasks if t[2] == project_id]

    my_projects = db.get_projects_by_employee(session['user_id'])
    reports = db.get_work_reports_by_employee(session['user_id'])

    return render_template('projects/my_tasks.html',
                           tasks=tasks,
                           my_projects=my_projects,
                           reports=reports,
                           selected_status=status_filter,
                           selected_project=project_id,
                           active_tab=active_tab)

# ========== MY WORK REPORTS (Redirect to Daily Tasks History) ==========
@projects_bp.route('/employee/my_work_reports')
def my_work_reports():
    if 'user_id' not in session or session['emp_type'] not in ['emp', 'tester']:
        return redirect(url_for('auth.login'))
    return redirect(url_for('tasks.employee_daily_tasks', tab='history'))

@projects_bp.route('/employee/submit_work_report', methods=['POST'])
def submit_work_report():
    if 'user_id' not in session or session['emp_type'] not in ['emp', 'tester']:
        return redirect(url_for('auth.login'))

    project_id = int(request.form['project_id'])
    task_id = int(request.form['task_id'])
    hours_worked = float(request.form['hours_worked'])
    work_description = request.form['work_description'].strip()
    progress_percentage = int(request.form['progress_percentage'])
    blocker = request.form.get('blocker', '').strip()
    tomorrow_plan = request.form.get('tomorrow_plan', '').strip()
    status_change = request.form.get('status_change', '') # e.g. 'in_review'

    # Security check: employee is assigned to task and project
    task = db.get_task(task_id)
    if not task or task[2] != project_id or task[3] != session['user_id']:
        flash('Error: Task verification failed. Cannot log work for this task.', 'error')
        return redirect(url_for('tasks.employee_daily_tasks', tab='history'))

    try:
        report_data = {
            'employee_id': session['user_id'],
            'project_id': project_id,
            'task_id': task_id,
            'hours_worked': hours_worked,
            'work_description': work_description,
            'progress_percentage': progress_percentage,
            'blocker': blocker or None,
            'tomorrow_plan': tomorrow_plan or None
        }
        db.add_work_report(report_data)

        # Handle status transition if employee requested it (like moving to review)
        if status_change in ['in_progress', 'in_review']:
            db.update_task_status_only(task_id, status_change, user_id=session['user_id'])

        flash('Daily work report submitted successfully.', 'success')
    except Exception as e:
        flash(f'Error logging work report: {str(e)}', 'error')

    return redirect(url_for('tasks.employee_daily_tasks', tab='history'))

@projects_bp.route('/employee/edit_work_report/<int:report_id>', methods=['POST'])
def edit_work_report(report_id):
    if 'user_id' not in session or session['emp_type'] not in ['emp', 'tester']:
        return redirect(url_for('auth.login'))

    hours_worked = float(request.form['hours_worked'])
    work_description = request.form['work_description'].strip()
    progress_percentage = int(request.form['progress_percentage'])
    blocker = request.form.get('blocker', '').strip()
    tomorrow_plan = request.form.get('tomorrow_plan', '').strip()

    try:
        report_data = {
            'hours_worked': hours_worked,
            'work_description': work_description,
            'progress_percentage': progress_percentage,
            'blocker': blocker or None,
            'tomorrow_plan': tomorrow_plan or None
        }
        db.update_work_report(report_id, report_data)
        flash('Work report updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating work report: {str(e)}', 'error')

    return redirect(url_for('tasks.employee_daily_tasks', tab='history'))
