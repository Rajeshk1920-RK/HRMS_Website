"""Task, task-detail, daily-task and status-master routes
(moved verbatim from app.py)."""
import math
import logging
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

from app.extensions import db
from app.filters import is_editable

logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/admin/view_tasks')
def view_tasks():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    # Pagination parameters
    page = int(request.args.get('page', 1))
    page_size = 10
    project_filter = request.args.get('project_filter', '')
    status_filter = request.args.get('status_filter', '')
    employee_filter = request.args.get('employee_filter', '')

    # Get paginated tasks and total task count
    tasks, total_tasks = db.get_all_tasks_with_details_paginated(page, page_size, project_filter, status_filter, employee_filter)
    employees = db.get_employees()
    projects = db.get_projects()

    # Calculate total pages
    total_pages = math.ceil(total_tasks / page_size)

    return render_template('tasks/view_tasks.html',
                         tasks=tasks,
                         employees=employees,
                         projects=projects,
                         page=page,
                         page_size=page_size,
                         total_tasks=total_tasks,
                         total_pages=total_pages,
                         project_filter=project_filter,
                         status_filter=status_filter,
                         employee_filter=employee_filter)

@tasks_bp.route('/admin/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    task = db.get_task(task_id)
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('tasks.view_tasks'))

    if request.method == 'POST':
        task_data = {
            'project_id': request.form['project_id'],
            'emp_id': request.form['emp_id'],
            'task_desc': request.form['task_desc'],
            'priority': request.form['priority'],
            'status': request.form['status'],
            'start_date': request.form['start_date'],
            'end_date': request.form['end_date']
        }

        try:
            db.update_task(task_id, task_data)
            flash('Task updated successfully!', 'success')
            return redirect(url_for('tasks.view_tasks'))
        except Exception as e:
            flash('Error updating task.', 'error')

    projects = db.get_projects()
    employees = db.get_employees()
    task_statuses = db.get_task_statuses()
    return render_template('tasks/edit_task.html', task=task, projects=projects, employees=employees, task_statuses=task_statuses)

@tasks_bp.route('/admin/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    try:
        db.delete_task(task_id)
        flash('Task deleted successfully!', 'success')
    except Exception as e:
        flash('Error deleting task.', 'error')

    return redirect(url_for('tasks.view_tasks'))

@tasks_bp.route('/admin/add_task', methods=['GET', 'POST'])
def add_task():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        task_data = {
            'project_id': request.form['project_id'],
            'emp_id': request.form['emp_id'],
            'task_desc': request.form['task_desc'],
            'priority': request.form['priority'],
            'status': request.form['status'],
            'start_date': request.form['start_date'],
            'end_date': request.form['end_date']
        }

        try:
            db.add_task(task_data)
            flash('Task added successfully!', 'success')
            return redirect(url_for('tasks.view_tasks'))
        except Exception as e:
            flash('Error adding task.', 'error')

    projects = db.get_projects()
    employees = db.get_employees()
    today = date.today().isoformat()  # format: 'YYYY-MM-DD'
    task_statuses = db.get_task_statuses()
    return render_template('tasks/add_task.html', projects=projects, employees=employees, today=today, task_statuses=task_statuses)

@tasks_bp.route('/employee/add_task_detail', methods=['POST'])
def add_task_detail():
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    task_id = request.form['task_id']
    desc = request.form['desc']
    status = request.form['status']

    try:
        # Check if an update already exists for today
        if db.has_task_detail_today(task_id, session['user_id']):
            flash('You have already added an update for this task today.', 'error')
            return redirect(url_for('tasks.view_task_details', task_id=task_id))

        db.add_task_detail(task_id, desc, status, session['user_id'])
        flash('Task update added successfully!', 'success')
    except Exception as e:
        flash('Error adding task update.', 'error')

    return redirect(url_for('tasks.view_task_details', task_id=task_id))

@tasks_bp.route('/employee/view_task_details/<int:task_id>')
def view_task_details(task_id):
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    task = db.get_task(task_id)
    if not task or task[3] != session['user_id']:  # Ensure task belongs to the employee
        flash('Task not found or you do not have permission to view it.', 'error')
        return redirect(url_for('employees.employee_dashboard'))

    details = db.get_task_details_by_employee(task_id, session['user_id'])
    project = db.get_project(task[2])  # Get project details for task
    return render_template('tasks/view_task_details.html', task=task, details=details, project=project)

@tasks_bp.route('/employee/edit_task_detail/<int:detail_id>', methods=['GET', 'POST'])
def edit_task_detail(detail_id):
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    detail = db.get_task_detail(detail_id)
    if not detail or not db.verify_task_detail_owner(detail_id, session['user_id']):
        flash('Task update not found or you do not have permission to edit it.', 'error')
        return redirect(url_for('employees.employee_dashboard'))

    if request.method == 'POST':
        desc = request.form['desc']
        status = request.form['status']

        try:
            db.update_task_detail(detail_id, desc, status)
            flash('Task update edited successfully!', 'success')
            return redirect(url_for('tasks.view_task_details', task_id=detail[1]))
        except Exception as e:
            flash('Error editing task update.', 'error')

    return render_template('tasks/edit_task_detail.html', detail=detail, task_id=detail[1])

@tasks_bp.route('/employee/daily_tasks', methods=['GET', 'POST'])
def employee_daily_tasks():
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    profile = db.get_employee_profile(session['user_id'])


    statuses = db.get_task_statuses()

    # Get search dates, default to current local date in IST
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    if not start_date or not end_date:
        # Default to today's date in IST (UTC+5:30)
        current_ist = (datetime.utcnow() + timedelta(hours=5, minutes=30)).date()
        current_ist_str = current_ist.strftime("%Y-%m-%d")
        if not start_date:
            start_date = current_ist_str
        if not end_date:
            end_date = current_ist_str

    if request.method == 'POST':
        if not statuses:
            flash("Cannot submit task. Wait for admin status update.", "error")
            return redirect(url_for('tasks.employee_daily_tasks'))
        title = request.form.get('task_title', '').strip()
        desc = request.form.get('task_desc', '').strip()
        project_status = request.form.get('project_status', '').strip()
        task_hours = request.form.get('task_hours', '').strip()

        if not title or not desc or not project_status or not task_hours:
            flash("All fields are required.", "error")
        else:
            try:
                hours_val = int(task_hours)
                if hours_val <= 0 or hours_val > 24:
                    raise ValueError
            except ValueError:
                flash("Hours must be a valid number between 1 and 24.", "error")
                return redirect(url_for('tasks.employee_daily_tasks', start_date=start_date, end_date=end_date))

            db.add_daily_task(session['user_id'], title, desc, project_status, hours_val)
            flash("Daily task submitted successfully!", "success")
            return redirect(url_for('tasks.employee_daily_tasks', start_date=start_date, end_date=end_date))

    daily_tasks = db.get_daily_tasks_by_employee(session['user_id'], start_date, end_date)

    # Group daily tasks by date (IST conversion)
    grouped_tasks = {}
    for task in daily_tasks:
        dt_val = task[5] # inserted_date
        if isinstance(dt_val, str):
            try:
                dt = datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    dt = datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    dt = datetime.utcnow() # fallback
        else:
            dt = dt_val

        # Convert to IST date
        ist_dt = dt + timedelta(hours=5, minutes=30)
        date_raw = ist_dt.strftime("%Y-%m-%d")
        display_date = ist_dt.strftime("%d-%m-%Y") # formatted as DD-MM-YYYY

        if date_raw not in grouped_tasks:
            grouped_tasks[date_raw] = {
                'date': display_date,
                'date_raw': date_raw,
                'tasks': [],
                'total_hours': 0,
                'count': 0
            }
        grouped_tasks[date_raw]['tasks'].append(task)
        grouped_tasks[date_raw]['total_hours'] += (task[7] or 0)
        grouped_tasks[date_raw]['count'] += 1

    summary_list = list(grouped_tasks.values())
    summary_list.sort(key=lambda x: x['date_raw'], reverse=True)

    return render_template('tasks/employee_daily_tasks.html',
                           daily_tasks=daily_tasks,
                           summary_list=summary_list,
                           statuses=statuses,
                           start_date=start_date,
                           end_date=end_date)

@tasks_bp.route('/employee/daily_task/edit/<int:task_id>', methods=['GET', 'POST'])
def edit_daily_task(task_id):
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    task = db.get_daily_task(task_id)
    if not task or task[1] != session['user_id']:
        flash("Daily task not found or unauthorized.", "error")
        return redirect(url_for('tasks.employee_daily_tasks'))

    # Check edit window limit using same calendar day rule
    if not is_editable(task[5]):
        flash("The editing window for this daily task has expired (only editable on the day of submission).", "error")
        return redirect(url_for('tasks.employee_daily_tasks'))

    statuses = db.get_task_statuses()

    if request.method == 'POST':
        if not statuses:
            flash("Cannot update task. Wait for admin status update.", "error")
            return redirect(url_for('tasks.employee_daily_tasks'))
        title = request.form.get('task_title', '').strip()
        desc = request.form.get('task_desc', '').strip()
        project_status = request.form.get('project_status', '').strip()
        task_hours = request.form.get('task_hours', '').strip()

        if not title or not desc or not project_status or not task_hours:
            flash("All fields are required.", "error")
        else:
            try:
                hours_val = int(task_hours)
                if hours_val <= 0 or hours_val > 24:
                    raise ValueError
            except ValueError:
                flash("Hours must be a valid number between 1 and 24.", "error")
                return render_template('tasks/edit_daily_task.html', task=task, statuses=statuses)

            db.update_daily_task(task_id, session['user_id'], title, desc, project_status, hours_val)
            flash("Daily task updated successfully!", "success")
            return redirect(url_for('tasks.employee_daily_tasks'))

    return render_template('tasks/edit_daily_task.html', task=task, statuses=statuses)

@tasks_bp.route('/employee/daily_task/delete/<int:task_id>', methods=['POST'])
def delete_daily_task(task_id):
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    task = db.get_daily_task(task_id)
    if not task or task[1] != session['user_id']:
        flash("Daily task not found or unauthorized.", "error")
        return redirect(url_for('tasks.employee_daily_tasks'))

    # Check delete window limit using same calendar day rule
    if not is_editable(task[5]):
        flash("The deletion window for this daily task has expired (only deletable on the day of submission).", "error")
        return redirect(url_for('tasks.employee_daily_tasks'))

    try:
        db.delete_daily_task(task_id, session['user_id'])
        flash("Daily task deleted successfully!", "success")
    except Exception as e:
        flash("Error deleting daily task.", "error")

    return redirect(url_for('tasks.employee_daily_tasks'))

@tasks_bp.route('/admin/daily_tasks')
def admin_daily_tasks():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    daily_tasks = db.get_all_daily_tasks()

    # Group daily tasks by employee and date (IST conversion)
    grouped_tasks = {}
    for task in daily_tasks:
        emp_id = task[1]
        first_name = task[7] or ''
        last_name = task[8] or ''
        emp_name = f"{first_name} {last_name}".strip()
        if not emp_name:
            emp_name = f"Employee {emp_id}"

        dt_val = task[5]  # inserted_date
        if isinstance(dt_val, str):
            try:
                dt = datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    dt = datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    dt = datetime.utcnow()
        else:
            dt = dt_val

        # Convert to IST date
        ist_dt = dt + timedelta(hours=5, minutes=30)
        date_raw = ist_dt.strftime("%Y-%m-%d")
        display_date = ist_dt.strftime("%d-%m-%Y")

        key = (emp_id, date_raw)
        if key not in grouped_tasks:
            grouped_tasks[key] = {
                'emp_id': emp_id,
                'employee_name': emp_name,
                'date': display_date,
                'date_raw': date_raw,
                'tasks': [],
                'total_hours': 0,
                'count': 0
            }
        grouped_tasks[key]['tasks'].append(task)
        grouped_tasks[key]['total_hours'] += (task[9] or 0)
        grouped_tasks[key]['count'] += 1

    summary_list = list(grouped_tasks.values())
    summary_list.sort(key=lambda x: (x['date_raw'], x['employee_name']), reverse=True)

    return render_template('tasks/admin_daily_tasks.html',
                           daily_tasks=daily_tasks,
                           summary_list=summary_list)


@tasks_bp.route('/admin/daily_task_details/<int:emp_id>/<string:task_date>')
def admin_daily_task_details(emp_id, task_date):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    employee = db.get_employee(emp_id)
    if not employee:
        flash('Employee not found.', 'error')
        return redirect(url_for('tasks.admin_daily_tasks'))

    emp_name = f"{employee[1]} {employee[2]}".strip()
    tasks = db.get_daily_tasks_by_employee_and_date(emp_id, task_date)

    # Format display date from YYYY-MM-DD to DD-MM-YYYY
    try:
        display_date = datetime.strptime(task_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        display_date = task_date

    # Calculate total hours
    total_hours = sum(t[9] or 0 for t in tasks)

    return render_template('tasks/admin_daily_task_details.html',
                           tasks=tasks,
                           employee_name=emp_name,
                           emp_id=emp_id,
                           task_date=task_date,
                           display_date=display_date,
                           total_hours=total_hours)


@tasks_bp.route('/admin/daily_task/feedback/<int:task_id>', methods=['POST'])
def admin_daily_task_feedback(task_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    feedback = request.form.get('admin_feedback', '').strip()
    db.update_daily_task_feedback(task_id, feedback)
    flash("Feedback updated successfully!", "success")

    # Redirect back to details page if emp_id and task_date are provided
    emp_id = request.form.get('emp_id')
    task_date = request.form.get('task_date')
    if emp_id and task_date:
        return redirect(url_for('tasks.admin_daily_task_details', emp_id=emp_id, task_date=task_date))
    return redirect(url_for('tasks.admin_daily_tasks'))

@tasks_bp.route('/api/task_details/<int:task_id>')
def get_task_details(task_id):
    try:
        if 'user_id' not in session:
            logger.warning(f"Unauthorized access attempt to task details for task_id {task_id}")
            return jsonify({'error': 'Unauthorized'}), 401

        # Verify task exists
        task = db.get_task(task_id)
        if not task:
            logger.warning(f"Task not found for task_id {task_id}")
            return jsonify({'error': 'Task not found'}), 404

        details = db.get_task_details(task_id)

        # Convert to list of dictionaries for JSON response
        details_list = []
        for detail in details:
            details_list.append({
                'detail_id': detail[0],
                'desc': detail[1],
                'inserted_date': detail[2] if detail[2] else None,  # Handle null dates
                'status': detail[3]
            })

        logger.debug(f"Successfully fetched {len(details_list)} task details for task_id {task_id}")
        return jsonify(details_list)

    except Exception as e:
        logger.error(f"Error in get_task_details for task_id {task_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@tasks_bp.route('/admin/show_task_details/<int:task_id>')
def show_task_details(task_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    task = db.get_task(task_id)
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('employees.admin_dashboard'))

    project = db.get_project(task[2])  # task[2] is project_id
    employee = db.get_employee(task[3])  # task[3] is emp_id
    task_details = db.get_task_details(task_id)  # Use existing get_task_details method

    return render_template('tasks/show_task_details.html', task=task, project=project, employee=employee, task_details=task_details)

@tasks_bp.route('/api/task_detail/<int:detail_id>')
def api_get_task_detail(detail_id):
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return jsonify({'error': 'Unauthorized'}), 401

    detail = db.get_task_detail(detail_id)
    if not detail or not db.verify_task_detail_owner(detail_id, session['user_id']):
        return jsonify({'error': 'Not found'}), 404

    task = db.get_task(detail[1])
    return jsonify({
        'detail_id': detail[0],
        'task_id': detail[1],
        'desc': detail[2],
        'status': detail[4],
        'task_name': task[1] if task else ''
    })

# ------ Task Status Master --------------------
@tasks_bp.route('/admin/task_statuses', methods=['GET', 'POST'])
def admin_task_statuses():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip()
        color_class = request.form['color_class'].strip()

        if not name:
            flash('Status Name cannot be empty.', 'error')
        else:
            success, msg = db.add_task_status(name, description, color_class)
            flash(msg, 'success' if success else 'error')
        return redirect(url_for('tasks.admin_task_statuses'))

    statuses = db.get_task_statuses()
    return render_template('admin/admin_task_statuses.html', statuses=statuses)

@tasks_bp.route('/admin/task_statuses/edit/<int:status_id>', methods=['POST'])
def edit_task_status(status_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    name = request.form['name'].strip()
    description = request.form['description'].strip()
    color_class = request.form['color_class'].strip()

    if not name:
        flash('Status Name cannot be empty.', 'error')
    else:
        success, msg = db.update_task_status(status_id, name, description, color_class)
        flash(msg, 'success' if success else 'error')
    return redirect(url_for('tasks.admin_task_statuses'))

@tasks_bp.route('/admin/task_statuses/delete/<int:status_id>')
def delete_task_status(status_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    db.delete_task_status(status_id)
    flash('Task status deleted successfully.', 'success')
    return redirect(url_for('tasks.admin_task_statuses'))


# ------ Employee Status Master ----------------
@tasks_bp.route('/admin/employee_statuses', methods=['GET', 'POST'])
def admin_employee_statuses():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip()
        color_class = request.form['color_class'].strip()

        if not name:
            flash('Status Name cannot be empty.', 'error')
        else:
            success, msg = db.add_employee_status(name, description, color_class)
            flash(msg, 'success' if success else 'error')
        return redirect(url_for('tasks.admin_employee_statuses'))

    statuses = db.get_employee_statuses()
    return render_template('admin/admin_employee_statuses.html', statuses=statuses)

@tasks_bp.route('/admin/employee_statuses/edit/<int:status_id>', methods=['POST'])
def edit_employee_status(status_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    name = request.form['name'].strip()
    description = request.form['description'].strip()
    color_class = request.form['color_class'].strip()

    if not name:
        flash('Status Name cannot be empty.', 'error')
    else:
        success, msg = db.update_employee_status(status_id, name, description, color_class)
        flash(msg, 'success' if success else 'error')
    return redirect(url_for('tasks.admin_employee_statuses'))

@tasks_bp.route('/admin/employee_statuses/delete/<int:status_id>')
def delete_employee_status(status_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    db.delete_employee_status(status_id)
    flash('Employee status deleted successfully.', 'success')
    return redirect(url_for('tasks.admin_employee_statuses'))


# ── Reports & Kanban ──────────────────────────────────────────────────────────

@tasks_bp.route('/employee/reports')
def employee_reports():
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))
        
    project_filter = request.args.get('project_filter', '')
    status_filter = request.args.get('status_filter', '')
    search_query = request.args.get('search_query', '')
        
    status_counts = db.get_employee_task_status_counts(session['user_id'], project_filter, search_query)
    recent_activities = db.get_recent_task_activities(limit=20, emp_id=session['user_id'], project_filter=project_filter, status_filter=status_filter, search_query=search_query)
    tasks = db.get_tasks_by_employee(session['user_id'], status_filter=status_filter, project_filter=project_filter, search_query=search_query)
    
    projects = db.get_projects()
    
    return render_template('tasks/employee_reports.html',
                           status_counts=status_counts,
                           recent_activities=recent_activities,
                           tasks=tasks,
                           projects=projects,
                           project_filter=project_filter,
                           status_filter=status_filter,
                           search_query=search_query)

@tasks_bp.route('/employee/kanban')
def employee_kanban():
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))
        
    tasks = db.get_tasks_by_employee(session['user_id'])
    return render_template('tasks/kanban_board.html', tasks=tasks, is_admin=False)


# ── API ───────────────────────────────────────────────────────────────────────

@tasks_bp.route('/api/update_task_status', methods=['POST'])
def update_task_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    task_id = data.get('task_id')
    new_status = data.get('status')
    
    if not task_id or not new_status:
        return jsonify({'error': 'Bad request'}), 400
        
    try:
        db.update_task_status_only(task_id, new_status)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

