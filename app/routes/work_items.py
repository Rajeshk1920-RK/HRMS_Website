from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.extensions import db

work_items_bp = Blueprint('work_items', __name__)

@work_items_bp.route('/work_items/view')
def view_work_items():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_role = session.get('emp_type')
    user_id = session.get('user_id')

    project_id = request.args.get('project_id', type=int)
    employee_id = request.args.get('employee_id', type=int)
    status = request.args.get('status')
    search = request.args.get('search')

    # If employee, they can only see their own assigned tasks
    if user_role == 'emp':
        employee_id = user_id

    work_items = db.get_work_items(project_id=project_id, employee_id=employee_id, status=status, search=search)
    projects = db.get_projects()
    employees = db.get_employees()

    return render_template('work_items/view_work_items.html',
                           work_items=work_items,
                           projects=projects,
                           employees=employees,
                           selected_project=project_id,
                           selected_employee=employee_id,
                           selected_status=status,
                           search_query=search)

@work_items_bp.route('/admin/add_work_item', methods=['GET', 'POST'])
def add_work_item():
    if 'user_id' not in session or session.get('emp_type') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        employee_id = request.form.get('employee_id', type=int)
        work_title = request.form.get('work_title', '').strip()
        description = request.form.get('description', '').strip()
        technical_description = request.form.get('technical_description', '').strip()
        estimated_hours = request.form.get('estimated_hours', type=float)

        if not project_id or not employee_id or not work_title:
            flash('Project, Assignee, and Work Title are required.', 'error')
        else:
            try:
                data = {
                    'project_id': project_id,
                    'employee_id': employee_id,
                    'work_title': work_title,
                    'description': description,
                    'technical_description': technical_description,
                    'estimated_hours': estimated_hours or 0.0,
                    'created_by': session['user_id']
                }
                db.add_work_item(data)
                flash('Work item created successfully.', 'success')
                return redirect(url_for('work_items.view_work_items'))
            except Exception as e:
                flash(f'Error creating work item: {str(e)}', 'error')

    projects = db.get_projects()
    employees = db.get_employees()
    return render_template('work_items/add_work_item.html', projects=projects, employees=employees)

@work_items_bp.route('/work_items/details/<int:work_item_id>', methods=['GET', 'POST'])
def work_item_details(work_item_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    work_item = db.get_work_item(work_item_id)
    if not work_item:
        flash('Work item not found.', 'error')
        return redirect(url_for('work_items.view_work_items'))

    # Access control: Developer can only view if assigned
    user_role = session.get('emp_type')
    user_id = session.get('user_id')
    if user_role == 'emp' and work_item[3] != user_id:
        flash('Access denied to this work item.', 'error')
        return redirect(url_for('work_items.view_work_items'))

    if request.method == 'POST':
        # Append progress update
        description = request.form.get('description', '').strip()
        if not description:
            flash('Update description cannot be empty.', 'error')
        else:
            try:
                db.add_work_item_detail(work_item_id, user_id, description)
                flash('Progress log added successfully.', 'success')
                return redirect(url_for('work_items.work_item_details', work_item_id=work_item_id))
            except Exception as e:
                flash(f'Error adding progress: {str(e)}', 'error')

    details = db.get_work_item_details(work_item_id)
    qa_history = db.get_work_item_qa_history(work_item_id)

    return render_template('work_items/work_item_details.html',
                           work_item=work_item,
                           details=details,
                           qa_history=qa_history)

@work_items_bp.route('/work_items/my_work')
def my_work_items():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    work_items = db.get_work_items(employee_id=user_id)
    return render_template('work_items/my_work_items.html', work_items=work_items)

@work_items_bp.route('/work_items/update_status/<int:work_item_id>/<string:status>')
def update_status(work_item_id, status):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    work_item = db.get_work_item(work_item_id)
    if not work_item:
        flash('Work item not found.', 'error')
        return redirect(url_for('work_items.view_work_items'))

    user_role = session.get('emp_type')
    user_id = session.get('user_id')

    # RBAC State Checks
    # 1. Developer starts work (New -> Active) or Developer submits for testing (Active -> Testing)
    if user_role == 'emp':
        if work_item[3] != user_id:
            flash('Not assigned to you.', 'error')
            return redirect(url_for('work_items.my_work_items'))
        
        if status == 'Active' and work_item[10] != 'New':
            flash('Invalid transition to Active.', 'error')
            return redirect(url_for('work_items.my_work_items'))
        
        if status == 'Testing' and work_item[10] != 'Active':
            flash('Invalid transition to Testing.', 'error')
            return redirect(url_for('work_items.my_work_items'))
            
        if status not in ['Active', 'Testing']:
            flash('Unauthorized state transition.', 'error')
            return redirect(url_for('work_items.my_work_items'))

    # Admin override or Tester confirmation of resolve (UAT -> Resolved)
    elif user_role == 'tester':
        if status == 'Resolved' and work_item[10] != 'UAT':
            flash('Only UAT items can be resolved.', 'error')
            return redirect(url_for('work_items.view_work_items'))
            
        if status not in ['Resolved']:
            flash('Unauthorized state transition.', 'error')
            return redirect(url_for('work_items.view_work_items'))

    try:
        db.update_work_item_status(work_item_id, status, user_id)
        flash(f'Status updated to {status} successfully.', 'success')
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')

    if user_role == 'emp':
        return redirect(url_for('work_items.my_work_items'))
    return redirect(url_for('work_items.work_item_details', work_item_id=work_item_id))

@work_items_bp.route('/work_items/qa_queue')
def qa_queue():
    if 'user_id' not in session or session.get('emp_type') not in ['admin', 'tester']:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('auth.login'))

    # Fetch tasks in Testing or UAT
    testing_items = db.get_work_items(status='Testing')
    uat_items = db.get_work_items(status='UAT')
    return render_template('work_items/qa_queue.html', testing_items=testing_items, uat_items=uat_items)

@work_items_bp.route('/work_items/perform_qa/<int:work_item_id>', methods=['GET', 'POST'])
def perform_qa(work_item_id):
    if 'user_id' not in session or session.get('emp_type') not in ['admin', 'tester']:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('auth.login'))

    work_item = db.get_work_item(work_item_id)
    if not work_item:
        flash('Work item not found.', 'error')
        return redirect(url_for('work_items.qa_queue'))

    if work_item[10] not in ['Testing', 'UAT']:
        flash('Work item is not ready for QA verification.', 'error')
        return redirect(url_for('work_items.work_item_details', work_item_id=work_item_id))

    if request.method == 'POST':
        result = request.form.get('result') # PASS or FAIL
        description = request.form.get('description', '').strip()

        if result not in ['PASS', 'FAIL']:
            flash('Invalid QA result.', 'error')
        elif not description:
            flash('QA feedback/description is required.', 'error')
        else:
            try:
                db.submit_qa_result(work_item_id, session['user_id'], result, description)
                flash('QA verification report submitted.', 'success')
                return redirect(url_for('work_items.qa_queue'))
            except Exception as e:
                flash(f'Error submitting QA: {str(e)}', 'error')

    return render_template('work_items/perform_qa.html', work_item=work_item)
