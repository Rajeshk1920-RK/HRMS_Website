"""Leave-type, leave-request and leave-summary routes
(moved verbatim from app.py)."""
import math
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

from app.extensions import db

leave_bp = Blueprint('leave', __name__)


# ------ Leave types ----------------------------------
@leave_bp.route('/admin/leave_types', methods=['GET', 'POST'])
def admin_leave_types():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    popup_message = None
    popup_type = None

    if request.method == 'POST':
        leave_type = request.form['leave_type'].strip()
        lt_id = request.form.get('leave_type_id')

        if not leave_type:
            popup_message = 'Leave type cannot be empty.'
            popup_type = 'error'
        elif lt_id:  # Edit
            success = db.update_leave_type(int(lt_id), leave_type)
            popup_message = 'Leave type updated successfully.' if success else 'Update failed.'
            popup_type = 'success' if success else 'error'
        else:  # Add
            success, message = db.add_leave_type(leave_type)
            popup_message = message
            popup_type = 'success' if success else 'error'

    edit_type = None
    edit_id = request.args.get('edit_id')
    if edit_id:
        leave_types_all = db.get_leave_types()
        edit_type = next((lt for lt in leave_types_all if str(lt[0]) == edit_id), None)
    else:
        leave_types_all = db.get_leave_types()

    return render_template('leave/admin_leave_types.html',
                           leave_types=leave_types_all,
                           popup_message=popup_message,
                           popup_type=popup_type,
                           edit_type=edit_type)

@leave_bp.route('/admin/delete_leave_type/<int:lt_id>')
def delete_leave_type(lt_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    db.delete_leave_type(lt_id)
    flash('Leave type deleted', 'success')
    return redirect(url_for('leave.admin_leave_types'))

# ------ Leave requests list & approval ---------------
@leave_bp.route('/admin/leave_requests')
def admin_leave_requests():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    filters = []
    params = []

    employee = request.args.get('employee', '').strip()
    if employee:
        filters.append("e.emp_id = %s")
        params.append(employee)

    ltype = request.args.get('type', '').strip()
    if ltype:
        filters.append("lt.leave_type_id = %s")
        params.append(ltype)

    status = request.args.get('status', '').strip()
    if status:
        filters.append("lr.status = %s")
        params.append(status)

    from_date = request.args.get('from_date', '').strip()
    if from_date:
        filters.append("DATE(lr.start_date) >= %s")
        params.append(from_date)

    to_date = request.args.get('to_date', '').strip()
    if to_date:
        filters.append("DATE(lr.end_date) <= %s")
        params.append(to_date)

    where = 'WHERE ' + ' AND '.join(filters) if filters else ''
    total = db.count_leave_requests(where, tuple(params))
    requests = db.get_leave_requests_paginated(where, tuple(params), limit=per_page, offset=offset)

    total_pages = math.ceil(total / per_page)

    # NEW: fetch options
    employees = db.get_employees(status_filter='active')
    leave_types = db.get_leave_types()

    return render_template('leave/admin_leave_requests.html',
                           requests=requests,
                           page=page,
                           total_pages=total_pages,
                           employees=employees,
                           leave_types=leave_types)

@leave_bp.route('/admin/leave_requests/<int:req_id>/<action>')
def update_leave_request(req_id, action):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    if action not in ('approved', 'rejected'):
        abort(400)
    db.update_leave_status(req_id, action, session['user_id'])
    flash(f'Request {action}', 'success')
    return redirect(url_for('leave.admin_leave_requests'))



@leave_bp.route('/employee/leave', methods=['GET', 'POST'])
def employee_leave():
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        data = {
            'leave_type_id': request.form['leave_type_id'],
            'employee_id':   session['user_id'],
            'start_date':    request.form['start_date'],
            'end_date':      request.form['end_date'],
            'leave_desc':    request.form['leave_desc'][:500],
            'manager_id':    None,                 # set later if you have manager mapping
        }
        db.add_leave_request(data)
        flash('Leave request submitted', 'success')
        return redirect(url_for('leave.employee_leave_requests'))

    leave_types = db.get_leave_types()
    my_requests = db.get_leave_requests('WHERE lr.employee_id=%s', (session['user_id'],))
    today_iso    = date.today().isoformat()          #  ← new

    return render_template('leave/employee_leave.html',
                           leave_types=leave_types, my_requests=my_requests, today=today_iso                          #  ← new
)

@leave_bp.route('/employee/my_leave_requests')
def employee_leave_requests():
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    my_requests = db.get_leave_requests('WHERE lr.employee_id=%s', (session['user_id'],))
    return render_template('leave/employee_leave_requests.html', my_requests=my_requests)

@leave_bp.route('/admin/leave_summary', methods=['GET', 'POST'])
def admin_leave_summary():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    # ---------- Grab filter values ----------
    f_date_from   = request.form.get('date_from')         if request.method == 'POST' else ''
    f_date_to     = request.form.get('date_to')           if request.method == 'POST' else ''
    f_leave_type  = request.form.get('leave_type_id')     if request.method == 'POST' else ''

    leave_types   = db.get_leave_types()
    summary       = db.get_leave_summary(
                        date_from   = f_date_from or None,
                        date_to     = f_date_to   or None,
                        leave_type_id = f_leave_type or None
                    )

    return render_template('leave/admin_leave_summary.html',
                           leave_types = leave_types,
                           summary     = summary,
                           f_date_from = f_date_from,
                           f_date_to   = f_date_to,
                           f_leave_type= f_leave_type)

@leave_bp.route('/admin/leave_requests/handle', methods=['POST'])
def handle_leave_action():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    req_id = request.form['request_id']
    action = request.form['action']
    comments = request.form['comments'][:200]

    current_status = db.get_leave_status(req_id)
    if current_status != 'pending':
        flash('Action not allowed. Leave request already processed.', 'error')
        return redirect(url_for('leave.admin_leave_requests'))

    db.update_leave_status(req_id, action, session['user_id'], comments)
    flash(f'Leave request {action}', 'success')
    return redirect(url_for('leave.admin_leave_requests'))


@leave_bp.route('/holidays')
def holidays():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('leave/holidays.html')

