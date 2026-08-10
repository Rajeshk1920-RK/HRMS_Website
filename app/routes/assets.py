"""Asset management routes (moved verbatim from app.py).

These routes use raw SQL through get_db_connection(), same as before.
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.extensions import get_db_connection

assets_bp = Blueprint('assets', __name__)


@assets_bp.route('/admin/add_asset', methods=['GET', 'POST'])
def add_asset():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO TblAssets (ItemName, Model, Price, Descriptions, Status) VALUES (%s, %s, %s, %s, %s)',
                     (request.form['item_name'], request.form['model'], request.form['price'], request.form['descriptions'], request.form['status']))
        conn.commit()
        conn.close()
        flash('Asset added successfully!', 'success')
        return redirect(url_for('assets.view_assets'))
    return render_template('assets/add_asset.html')

@assets_bp.route('/admin/view_assets')
def view_assets():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM TblAssets')
    assets = cursor.fetchall()
    conn.close()
    return render_template('assets/view_assets.html', assets=assets)

@assets_bp.route('/admin/edit_asset/<int:asset_id>', methods=['GET', 'POST'])
def edit_asset(asset_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM TblAssets WHERE AssetId = %s', (asset_id,))
    asset = cursor.fetchone()
    if request.method == 'POST':
        cursor.execute('UPDATE TblAssets SET ItemName=%s, Model=%s, Price=%s, Descriptions=%s, Status=%s WHERE AssetId=%s',
                     (request.form['item_name'], request.form['model'], request.form['price'], request.form['descriptions'], request.form['status'], asset_id))
        conn.commit()
        conn.close()
        flash('Asset updated successfully!', 'success')
        return redirect(url_for('assets.view_assets'))
    conn.close()
    return render_template('assets/edit_asset.html', asset=asset)

@assets_bp.route('/admin/delete_asset/<int:asset_id>')
def delete_asset(asset_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM TblAssets WHERE AssetId = %s', (asset_id,))
    conn.commit()
    conn.close()
    flash('Asset deleted successfully!', 'success')
    return redirect(url_for('assets.view_assets'))

@assets_bp.route('/admin/allocate_asset', methods=['GET', 'POST'])
def allocate_asset():
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TblAssets WHERE Status = 'Available'")
    assets = cursor.fetchall()
    cursor.execute("SELECT emp_id, first_name, last_name FROM tbl_employee WHERE status != 'inactive'")
    employees = cursor.fetchall()

    selected_asset_id = request.args.get('asset_id', type=int)

    if request.method == 'POST':
        cursor.execute('''
            INSERT INTO TblAllocateAssets (AssetId, EmployeeId, AllocateDate, Status, AllocatedBy, Description)
            VALUES (%s, %s, CURRENT_DATE, 'Allocated', %s, %s)
        ''', (
            request.form['asset_id'],
            request.form['employee_id'],
            request.form['allocated_by'],
            request.form['description']
        ))
        cursor.execute("UPDATE TblAssets SET Status = 'Allocated' WHERE AssetId = %s", (request.form['asset_id'],))
        conn.commit()
        conn.close()
        flash("Asset allocated successfully", "success")
        return redirect(url_for('assets.manage_allocation'))

    conn.close()
    return render_template(
        'assets/allocate_asset.html',
        assets=assets,
        employees=employees,
        selected_asset_id=selected_asset_id
    )

@assets_bp.route('/admin/manage_allocation')
def manage_allocation():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT aa.*, a.ItemName, a.Model, e.first_name, e.last_name,
            (
                SELECT STRING_AGG(IssueId::text || '##' || IssueText, '||')
                FROM TblAssetIssues
                WHERE AssetId = aa.AssetId AND EmployeeId = aa.EmployeeId AND Status = 'Open'
            ) AS Issues
        FROM TblAllocateAssets aa
        JOIN TblAssets a ON aa.AssetId = a.AssetId
        JOIN tbl_employee e ON aa.EmployeeId = e.emp_id
        ORDER BY aa.AllocateDate DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return render_template('assets/manage_allocation.html', allocations=rows)

@assets_bp.route('/admin/edit_allocation/<int:alloc_id>', methods=['GET', 'POST'])
def edit_allocation(alloc_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT aa.*, a.ItemName, a.Model, e.first_name, e.last_name
        FROM TblAllocateAssets aa
        JOIN TblAssets a ON aa.AssetId = a.AssetId
        JOIN tbl_employee e ON aa.EmployeeId = e.emp_id
        WHERE aa.AllocatedId = %s
    ''', (alloc_id,))
    allocation = cursor.fetchone()

    if request.method == 'POST':
        cursor.execute("UPDATE TblAllocateAssets SET Status = 'Returned' WHERE AllocatedId = %s", (alloc_id,))
        cursor.execute("UPDATE TblAssets SET Status = 'Available' WHERE AssetId = %s", (allocation['AssetId'],))
        conn.commit()
        conn.close()
        flash("Asset returned", "success")
        return redirect(url_for('assets.manage_allocation'))

    conn.close()
    return render_template('assets/edit_allocation.html', allocation=allocation)

@assets_bp.route('/admin/asset_history', methods=['GET'])
def asset_history():
    selected_emp_id = request.args.get('employee_id', type=int)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT emp_id, first_name, last_name FROM tbl_employee WHERE status != 'inactive'")
    employees = cursor.fetchall()
    history = []
    if selected_emp_id:
        cursor.execute('''
            SELECT aa.*, a.ItemName, a.Model FROM TblAllocateAssets aa
            JOIN TblAssets a ON aa.AssetId = a.AssetId
            WHERE aa.EmployeeId = %s
            ORDER BY aa.AllocateDate DESC
        ''', (selected_emp_id,))
        history = cursor.fetchall()
    conn.close()
    return render_template('assets/asset_history.html', employees=employees, history=history, selected_emp_id=selected_emp_id)

@assets_bp.route('/employee/assets')
def employee_assets():
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT aa.*, a.ItemName, a.Model
        FROM TblAllocateAssets aa
        JOIN TblAssets a ON aa.AssetId = a.AssetId
        WHERE aa.EmployeeId = %s AND aa.Status = 'Allocated'
        ORDER BY aa.AllocateDate DESC
    ''', (session['user_id'],))
    assets = cursor.fetchall()

    cursor.execute('''
        SELECT * FROM TblAssetIssues
        WHERE EmployeeId = %s
        ORDER BY ReportedDate DESC
    ''', (session['user_id'],))
    issues = cursor.fetchall()
    conn.close()

    # Group issues by asset ID and status
    open_issues_by_asset = {}
    resolved_issues_by_asset = {}

    for i in issues:
        if i['Status'] == 'Resolved':
            resolved_issues_by_asset.setdefault(i['AssetId'], []).append(i)
        else:
            open_issues_by_asset.setdefault(i['AssetId'], []).append(i)

    return render_template('assets/employee_assets.html',
                           assets=assets,
                           open_issues_by_asset=open_issues_by_asset,
                           resolved_issues_by_asset=resolved_issues_by_asset)

@assets_bp.route('/employee/report_issue/<int:asset_id>', methods=['POST'])
def report_asset_issue(asset_id):
    if 'user_id' not in session or session['emp_type'] != 'emp':
        return redirect(url_for('auth.login'))

    issue_text = request.form['issue_text'].strip()
    if issue_text:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO TblAssetIssues (AssetId, EmployeeId, IssueText)
            VALUES (%s, %s, %s)
        ''', (asset_id, session['user_id'], issue_text))
        conn.commit()
        conn.close()
        flash('Issue reported successfully', 'success')
    else:
        flash('Issue text cannot be empty.', 'error')

    return redirect(url_for('assets.employee_assets'))

@assets_bp.route('/admin/resolve_issue/<int:issue_id>', methods=['POST'])
def resolve_issue(issue_id):
    if 'user_id' not in session or session['emp_type'] != 'admin':
        return redirect(url_for('auth.login'))

    comment = request.form.get('resolved_comment', '').strip()

    if not comment:
        flash('Resolution comment is required.', 'error')
        return redirect(url_for('assets.manage_allocation'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE TblAssetIssues
        SET Status = 'Resolved',
            ResolvedComment = %s,
            ResolvedDate = CURRENT_DATE
        WHERE IssueId = %s
    ''', (comment, issue_id))
    conn.commit()
    conn.close()

    flash('Issue marked as resolved.', 'success')
    return redirect(url_for('assets.manage_allocation'))
