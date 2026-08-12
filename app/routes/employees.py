"""Dashboard, employee CRUD, registration-request, profile and quick-delete
routes (moved verbatim from app.py)."""
import math
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.extensions import db

employees_bp = Blueprint('employees', __name__)


@employees_bp.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    stats = db.get_project_dashboard_stats()
    
    # Get filters
    domain = request.args.get('domain', '').strip()
    status = request.args.get('status', '').strip()
    pm_id = request.args.get('pm_id', type=int)
    priority = request.args.get('priority', '').strip()
    
    projects = db.get_projects_filtered(
        domain=domain or None,
        status=status or None,
        pm_id=pm_id or None,
        priority=priority or None
    )
    
    # Calculate health for projects in dashboard table
    projects_with_health = []
    for p in projects:
        health = db.get_project_health(p[0])
        projects_with_health.append(list(p) + [health])

    employees = db.get_employees()
    return render_template('projects/project_dashboard.html',
                           stats=stats,
                           projects=projects_with_health,
                           employees=employees,
                           selected_domain=domain,
                           selected_status=status,
                           selected_pm=pm_id,
                           selected_priority=priority)

@employees_bp.route('/admin/registration_requests')
def registration_requests():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    status_filter = request.args.get('status', 'pending')
    reqs = db.get_registration_requests(status=status_filter)
    return render_template('employees/registration_requests.html', requests=reqs, status_filter=status_filter)

@employees_bp.route('/admin/reject_registration/<int:req_id>')
def reject_registration(req_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    try:
        db.update_registration_status(req_id, 'rejected')
        flash('Registration request rejected successfully.', 'success')
    except Exception as e:
        flash(f'Error rejecting request: {e}', 'error')

    return redirect(url_for('employees.registration_requests'))

@employees_bp.route('/admin/reaccept_registration/<int:req_id>')
def reaccept_registration(req_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    try:
        db.update_registration_status(req_id, 'pending')
        flash('Registration request reaccepted/restored to pending.', 'success')
    except Exception as e:
        flash(f'Error reaccepting request: {e}', 'error')

    return redirect(url_for('employees.registration_requests', status='pending'))

@employees_bp.route('/admin/view_employees')
def view_employees():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    status_filter = request.args.get('status_filter', 'all')
    employees = db.get_employees(status_filter=status_filter)

    return render_template('employees/view_employees.html', employees=employees, status_filter=status_filter)

@employees_bp.route('/admin/edit_employee/<int:emp_id>', methods=['GET', 'POST'])
def edit_employee(emp_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    employee = db.get_employee(emp_id)
    if not employee:
        flash('Employee not found.', 'error')
        return redirect(url_for('employees.view_employees'))

    if request.method == 'POST':
        employee_data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'gender': request.form['gender'],
            'dob': request.form['dob'],
            'address': request.form['address'],
            'phone_no': request.form['phone_no'],
            'email': request.form['email'],
            'password': request.form['password'],
            'status': request.form['status'],
            'emp_type': request.form['emp_type']
        }

        try:
            db.update_employee(emp_id, employee_data)
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('employees.view_employees'))
        except Exception as e:
            flash('Error updating employee. Email might already exist.', 'error')

    employee_statuses = db.get_employee_statuses()
    return render_template('employees/edit_employee.html', employee=employee, employee_statuses=employee_statuses)

@employees_bp.route('/admin/delete_employee/<int:emp_id>')
def delete_employee(emp_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    try:
        db.delete_employee(emp_id)
        flash('Employee deleted successfully!', 'success')
    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('employees.view_employees'))

@employees_bp.route('/admin/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    req_id = request.args.get('req_id') or request.form.get('req_id')
    prefill = {}

    if req_id:
        req_data = db.get_registration_request(req_id)
        if req_data:
            # req_data: request_id, first_name, last_name, gender, dob, address, phone_no, email, password, department, status, inserted_date
            prefill = {
                'first_name': req_data[1],
                'last_name': req_data[2],
                'gender': req_data[3],
                'dob': req_data[4],
                'address': req_data[5],
                'phone_no': req_data[6],
                'email': req_data[7],
                'password': req_data[8],
                'department': req_data[9]
            }

    if request.method == 'POST':
        email_val = request.form.get('email', '').strip()
        if not email_val:
            from app.utils import generate_login_id
            email_val = generate_login_id(
                request.form.get('first_name', ''),
                request.form.get('last_name', ''),
                request.form.get('phone_no', '')
            )

        employee_data = {
            'first_name': request.form.get('first_name', ''),
            'last_name': request.form.get('last_name', ''),
            'gender': request.form.get('gender', ''),
            'dob': request.form.get('dob', ''),
            'address': request.form.get('address', ''),
            'phone_no': request.form.get('phone_no', ''),
            'email': email_val,
            'password': request.form.get('password', ''),
            'status': request.form.get('status', 'Active'),
            'emp_type': request.form.get('emp_type', 'emp'),
            'department': request.form.get('department')
        }

        try:
            emp_id = db.add_employee(employee_data)
            if req_id:
                db.update_registration_status(req_id, 'approved')
            flash('Employee added successfully!', 'success')
            return redirect(url_for('employees.manage_profile', emp_id=emp_id))
        except Exception as e:
            flash(f'Error adding employee: {str(e)}', 'error')
            prefill = employee_data

    employee_statuses = db.get_employee_statuses()
    return render_template('employees/add_employee.html', prefill=prefill, req_id=req_id, employee_statuses=employee_statuses)

@employees_bp.route('/employee/dashboard')
def employee_dashboard():
    if 'user_id' not in session or session['emp_type'] not in ['emp', 'tester']:
        return redirect(url_for('auth.login'))

    profile = db.get_employee_profile(session['user_id'])

    # 🔐 Restrict sidebar if:
    # - EmgContact is blank
    # - OR employee never updated it
    emg_missing = (
        not profile
        or not profile.get('EmgContact')
        or profile.get('EmgUpdatedByEmp') == 0
    )

    session['emg_missing'] = False  # Ensure sidebar links are never disabled

    status_filter = request.args.get('status_filter', 'all')
    tasks = db.get_tasks_by_employee(session['user_id'], status_filter=status_filter)
    today = date.today()  # Get current date
    approved_leaves = db.get_leave_requests(
        'WHERE lr.employee_id=%s AND lr.status=%s AND lr.end_date >= %s',
        (session['user_id'], 'approved', today)
    )
    return render_template('dashboard/employee_dashboard.html', tasks=tasks, emg_missing=emg_missing, status_filter=status_filter, today=today, approved_leaves=approved_leaves)

@employees_bp.route('/employee/my_profile', methods=['GET', 'POST'])
def employee_profile_view():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    emp_id = session['user_id']
    employee = db.get_employee(emp_id)
    profile = db.get_employee_profile(emp_id)
    work_hours = db.get_employee_work_hours(emp_id)

    if request.method == 'POST':
        import os
        from werkzeug.utils import secure_filename
        from datetime import datetime

        data = {
            'first_name': request.form.get('first_name', '').strip(),
            'last_name': request.form.get('last_name', '').strip(),
            'phone_no': request.form.get('phone_no', '').strip(),
            'email': request.form.get('email', '').strip(),
            'gender': request.form.get('gender', '').strip(),
            'dob': request.form.get('dob', '').strip(),
            'address': request.form.get('address', '').strip(),
            'password': request.form.get('password', '').strip(),
            'EmgContact': request.form.get('EmgContact', '').strip(),
            'profile_photo': None
        }

        # Check for profile photo upload
        file = request.files.get('profile_photo')
        if file and file.filename:
            from app.config import PROFILE_PHOTO_FOLDER
            filename = secure_filename(f"{emp_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file_path = os.path.join(PROFILE_PHOTO_FOLDER, filename)
            file.save(file_path)
            data['profile_photo'] = f"static/profile_photos/{filename}"

        try:
            db.update_employee_self(emp_id, data)
            
            # Immediately update the session names to reflect in layouts
            session['first_name'] = data['first_name'].title()
            session['last_name'] = data['last_name'].title()
            if data['profile_photo']:
                session['profile_photo'] = data['profile_photo']
            
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')

        return redirect(url_for('employees.employee_profile_view'))

    return render_template('employees/my_profile.html', employee=employee, profile=profile, work_hours=work_hours)

@employees_bp.route('/admin/employee_profile/<int:emp_id>', methods=['GET', 'POST'])
def manage_profile(emp_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    employee = db.get_employee(emp_id)
    if not employee:
        flash("Employee not found", "error")
        return redirect(url_for('employees.view_employees'))

    profile = db.get_employee_profile(emp_id)
    work_hours = db.get_employee_work_hours(emp_id)

    if request.method == 'POST':
        import os
        from werkzeug.utils import secure_filename
        from datetime import datetime

        data = {
            'EmployeeId': emp_id,
            'UANNo': request.form.get('UANNo', '').strip(),
            'PANNO': request.form.get('PANNO', '').strip(),
            'AadharNo': request.form.get('AadharNo', '').strip(),
            'BankName': request.form.get('BankName', '').strip(),
            'BranchName': request.form.get('BranchName', '').strip(),
            'ACNo': request.form.get('ACNo', '').strip(),
            'IFSCode': request.form.get('IFSCode', '').strip(),
            'Designation': request.form.get('Designation', '').strip(),
            'EmgContact': request.form.get('EmgContact', '').strip(),
            'ReportingMng': request.form.get('ReportingMng', '').strip(),
            'DOJ': request.form.get('DOJ', '').strip() or None,
            'PrgLng': request.form.get('PrgLng', '').strip(),
            'FrmWrk': request.form.get('FrmWrk', '').strip()
        }
        
        # Check if photo was uploaded
        file = request.files.get('profile_photo')
        if file and file.filename:
            from app.config import PROFILE_PHOTO_FOLDER
            filename = secure_filename(f"{emp_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file_path = os.path.join(PROFILE_PHOTO_FOLDER, filename)
            file.save(file_path)
            db.update_employee_profile_photo(emp_id, f"static/profile_photos/{filename}")

        if profile:
            db.update_employee_profile(emp_id, data)
        else:
            db.add_employee_profile(data)
            
        flash("Employee profile saved successfully!", "success")
        return redirect(url_for('employees.view_employees'))

    return render_template('employees/employee_profile.html', employee=employee, profile=profile, work_hours=work_hours)

@employees_bp.route('/admin/quick_delete', methods=['GET'])
def admin_quick_delete():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    category = request.args.get('category')
    data = []

    if category == 'employee':
        data = db.get_employees()
    elif category == 'task':
        data, _ = db.get_all_tasks_with_details_paginated(1, 9999)
    elif category == 'leave_type':
        data = db.get_leave_types()
    elif category == 'expense_type':
        data = db.get_expense_types()
    elif category == 'sub_expense_type':
        data = db.get_sub_expense_types()


    return render_template('admin/admin_quick_delete.html', category=category, data=data)

@employees_bp.route('/admin/delete_all/<category>', methods=['POST'])
def delete_all_category(category):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    try:
        if category == 'employee':
            db.delete_all_employees()
        elif category == 'task':
            db.delete_all_tasks()
        elif category == 'leave_type':
            db.delete_all_leave_types()
        elif category == 'expense_type':
            db.delete_all_expense_types()
        elif category == 'sub_expense_type':
            db.delete_all_sub_expense_types()
        flash(f'All {category.replace("_", " ")}s deleted.', 'success')
    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('employees.admin_quick_delete', category=category))

@employees_bp.route('/timesheet', methods=['GET', 'POST'])
@employees_bp.route('/timesheet/<int:emp_id>', methods=['GET', 'POST'])
def timesheet(emp_id=None):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    current_user_id = session['user_id']
    is_admin = (session.get('emp_type') == 'admin')

    if emp_id is None:
        emp_id = current_user_id
    elif emp_id != current_user_id and not is_admin:
        from flask import abort
        abort(403)

    if request.method == 'POST':
        submit_action = request.form.get('action')
        if submit_action == 'leave':
            data = {
                'leave_type_id': request.form.get('leave_type_id'),
                'employee_id': emp_id,
                'start_date': request.form.get('start_date'),
                'end_date': request.form.get('end_date'),
                'leave_desc': request.form.get('leave_desc', '')[:500],
                'day_period': request.form.get('day_period'),
                'phone_no': request.form.get('phone_no'),
                'notify_emails': request.form.get('notify_emails'),
                'manager_id': None
            }
            try:
                db.add_leave_request(data)
                flash('Leave request submitted successfully!', 'success')
            except Exception as e:
                flash(f'Error submitting leave request: {e}', 'error')
        
        elif submit_action == 'regularise':
            title = request.form.get('task_title', '').strip()
            desc = request.form.get('task_desc', '').strip()
            project_status = request.form.get('project_status', '').strip()
            task_hours = request.form.get('task_hours', '').strip()
            task_date = request.form.get('task_date', '').strip()
            
            if not title or not desc or not project_status or not task_hours or not task_date:
                flash('All fields are required for regularisation.', 'error')
            else:
                try:
                    hours_val = int(task_hours)
                    db.add_daily_task(emp_id, title, desc, project_status, hours_val, task_date=task_date)
                    flash('Attendance regularised and task logged successfully!', 'success')
                except Exception as e:
                    flash(f'Error regularising attendance: {e}', 'error')

        return redirect(url_for('employees.timesheet', emp_id=emp_id))

    employee = db.get_employee(emp_id)
    leave_types = db.get_leave_types()
    projects = db.get_projects()
    task_statuses = db.get_task_statuses()

    # Pre-populate dates for the calendar default (Aug 2026 or current)
    from datetime import datetime
    year = int(request.args.get('year', 2026))
    month = int(request.args.get('month', 8))

    return render_template('employees/timesheet.html', 
                           employee=employee, 
                           leave_types=leave_types, 
                           projects=projects,
                           task_statuses=task_statuses,
                           emp_id=emp_id,
                           year=year,
                           month=month)

@employees_bp.route('/api/timesheet_data/<int:emp_id>')
def api_timesheet_data(emp_id):
    from flask import jsonify
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    current_user_id = session['user_id']
    is_admin = (session.get('emp_type') == 'admin')
    if emp_id != current_user_id and not is_admin:
        return jsonify({'error': 'Forbidden'}), 403

    from datetime import datetime, date, timedelta
    import calendar

    try:
        year = int(request.args.get('year', 2026))
        month = int(request.args.get('month', 8))
    except ValueError:
        return jsonify({'error': 'Invalid year or month'}), 400

    public_holidays = {
        '2026-01-15': 'Makara Sankranti',
        '2026-01-26': 'Republic Day',
        '2026-03-19': 'Ugadi Festival',
        '2026-03-21': 'Khutub-E-Ramzan',
        '2026-05-01': 'May Day',
        '2026-05-28': 'Bakrid',
        '2026-08-15': 'Independence Day',
        '2026-08-26': 'Eid-Milad',
        '2026-10-02': 'Gandhi Jayanthi',
        '2026-10-20': 'Mahannavami, Ayudha Pooja',
        '2026-11-10': 'Balipadyami, Deepavali',
        '2026-12-25': 'Christmas'
    }
    restricted_holidays = {
        '2026-02-04': 'Shah-e-Barath',
        '2026-03-02': 'Holi Festival',
        '2026-03-17': 'Shab-e-Qadar',
        '2026-03-27': 'Sri Ramanavami',
        '2026-03-31': 'Mahaveera Jayanthi',
        '2026-04-03': 'Good Friday',
        '2026-04-14': 'Dr. B.R. Ambedkar Jayanthi',
        '2026-04-20': 'Basava Jayanthi',
        '2026-06-26': 'Last Day of Moharam',
        '2026-08-28': 'Raksha Bandhan',
        '2026-10-21': 'Vijayadasami',
        '2026-11-27': 'Kanakadasa Jayanthi',
        '2026-11-24': 'Guru Nanak Jayanthi'
    }

    conn = db.get_connection()
    cursor = conn.cursor()
    
    start_date = f"{year:04d}-{month:02d}-01"
    _, last_day = calendar.monthrange(year, month)
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"

    cursor.execute('''
        SELECT inserted_date::date, SUM(task_hours)
        FROM tbl_daily_task
        WHERE emp_id = %s AND inserted_date::date BETWEEN %s AND %s
        GROUP BY inserted_date::date
    ''', (emp_id, start_date, end_date))
    tasks = {str(row[0]): int(row[1]) for row in cursor.fetchall()}

    cursor.execute('''
        SELECT lr.start_date, lr.end_date, lt.leave_type, lr.status
        FROM tbl_leave_request lr
        JOIN tbl_leave_type lt ON lt.leave_type_id = lr.leave_type_id
        WHERE lr.employee_id = %s AND lr.status = 'approved'
          AND NOT (lr.end_date < %s OR lr.start_date > %s)
    ''', (emp_id, start_date, end_date))
    leaves = cursor.fetchall()
    
    conn.close()

    d_start = date(year, month, 1)
    d_end = date(year, month, last_day)
    
    calendar_data = {}
    curr = d_start
    while curr <= d_end:
        curr_str = str(curr)
        is_weekend = (curr.weekday() in (5, 6))
        is_pub_holiday = curr_str in public_holidays
        is_rest_holiday = curr_str in restricted_holidays
        
        covered_leave = None
        for lf in leaves:
            lf_start, lf_end, lf_type, lf_status = lf
            if lf_start <= curr <= lf_end:
                covered_leave = lf_type
                break
        
        hours = tasks.get(curr_str, 0)
        
        status = 'absent'
        desc = ''
        
        if hours > 0:
            if covered_leave or is_pub_holiday or is_rest_holiday:
                status = 'multiple_events'
                desc = 'Logged hours during leave/holiday'
            else:
                status = 'present'
        elif covered_leave:
            status = 'leave'
            desc = f"Approved Leave: {covered_leave}"
        elif is_pub_holiday:
            status = 'holiday'
            desc = f"Public Holiday: {public_holidays[curr_str]}"
        elif is_rest_holiday:
            status = 'holiday'
            desc = f"Restricted Holiday: {restricted_holidays[curr_str]}"
        elif is_weekend:
            status = 'weekly_off'
        else:
            status = 'absent'

        calendar_data[curr_str] = {
            'status': status,
            'hours': hours,
            'description': desc
        }
        curr += timedelta(days=1)

    return jsonify(calendar_data)
