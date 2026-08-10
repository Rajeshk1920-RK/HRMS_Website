"""Authentication routes (moved verbatim from app.py)."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

from app.extensions import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if 'user_id' in session:
        if session['emp_type'] == 'admin':
            return redirect(url_for('employees.admin_dashboard'))
        else:
            return redirect(url_for('employees.employee_dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        if session['emp_type'] == 'admin':
            return redirect(url_for('employees.admin_dashboard'))
        else:
            return redirect(url_for('employees.employee_profile_view'))

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        gender = request.form['gender']
        dob = request.form['dob']
        address = request.form['address']
        phone_no = request.form['phone_no']
        email = request.form.get('email', '').strip()
        if not email:
            from app.utils import generate_login_id
            email = generate_login_id(first_name, last_name, phone_no)

        password = request.form['password']
        department = request.form['department']

        try:
            db.add_registration_request({
                'first_name': first_name,
                'last_name': last_name,
                'gender': gender,
                'dob': dob,
                'address': address,
                'phone_no': phone_no,
                'email': email,
                'password': password,
                'department': department
            })
            flash('Registration request submitted successfully! Pending admin approval.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash('Error submitting registration request. Login ID may already exist.', 'error')

    return render_template('auth/register.html')

@auth_bp.route('/api/check-registration-status', methods=['POST'])
def api_check_registration_status():
    email = request.json.get('email', '').strip()
    if not email:
        return jsonify({'success': False, 'message': 'Login ID is required'}), 400

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT first_name, last_name, status, inserted_date, department
        FROM tbl_registration_requests
        WHERE email = %s
        ORDER BY inserted_date DESC
        LIMIT 1
    ''', (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'success': False, 'message': 'No registration request found for this Login ID.'})

    first_name, last_name, status, inserted_date, department = row
    return jsonify({
        'success': True,
        'first_name': first_name,
        'last_name': last_name,
        'status': status,
        'inserted_date': inserted_date,
        'department': department
    })

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form['password']

        user = db.verify_user(email, password)

        if user:
            session['user_id'] = user[0]
            session['first_name'] = user[1].title() if user[1] else ''
            session['last_name'] = user[2].title() if user[2] else ''
            session['emp_type'] = user[3]

            if user[3] == 'admin':
                return redirect(url_for('employees.admin_dashboard'))
            else:
                return redirect(url_for('employees.employee_profile_view'))
        else:
            flash('Invalid Login ID or password', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
