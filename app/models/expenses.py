"""Expense-type, expense and sub-expense-type data-access methods
(moved verbatim from database.py)."""
import psycopg2
from datetime import datetime
import pytz


class ExpenseMixin:
        # ========== EXPENSE TYPE ================================================
    def add_expense_type(self, etype):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('INSERT INTO tbl_expense_type (expense_type) VALUES (%s) ON CONFLICT (expense_type) DO NOTHING', (etype,))

    def get_expense_types(self):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('SELECT expense_type_id, expense_type FROM tbl_expense_type ORDER BY expense_type')
                return c.fetchall()

    def delete_expense_type(self, et_id):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('DELETE FROM tbl_expense_type WHERE expense_type_id=%s', (et_id,))

    def update_expense_type(self, et_id, new_type):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('UPDATE tbl_expense_type SET expense_type = %s WHERE expense_type_id = %s', (new_type, et_id))

    def expense_type_exists(self, etype, exclude_id=None):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                if exclude_id:
                    c.execute(
                        'SELECT 1 FROM tbl_expense_type WHERE expense_type = %s AND expense_type_id != %s',
                        (etype, exclude_id)
                    )
                else:
                    c.execute(
                        'SELECT 1 FROM tbl_expense_type WHERE expense_type = %s',
                        (etype,)
                    )
                return c.fetchone() is not None



    # ========== EXPENSES ====================================================
    def add_expense(self, data):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('''
                    INSERT INTO tbl_expenses
                    (expense_type_id, sub_expense_type_id, employee_id, exp_description,
                    manager_id, approver_comments, given_by_id, final_comments, amount,
                    inserted_date, expense_date, invoice_path, po_no, bill_status, expense_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    data['expense_type_id'],
                    data.get('sub_expense_type_id'),
                    data['employee_id'],
                    data['exp_description'],
                    data.get('manager_id'),
                    data.get('approver_comments', ''),
                    data.get('given_by_id'),
                    data.get('final_comments', ''),
                    data['amount'],
                    datetime.now(pytz.utc).isoformat(),
                    data['expense_date'],
                    data.get('invoice_path'),
                    data.get('po_no', ''),
                    data.get('bill_status', ''),
                    data.get('expense_by', '')
                ))
    def get_expenses(self, where='', params=()):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                q = f'''
                    SELECT ex.expense_id, et.expense_type,
                        e.first_name||' '||e.last_name AS emp_name,
                        ex.exp_description, ex.status,
                        ex.approver_comments, ex.final_comments,
                        ex.inserted_date, ex.amount,
                        ex.employee_id,
                        ex.approved_date,
                        ex.approved_by,
                        ex.expense_date,
                        ex.invoice_path
                    FROM   tbl_expenses ex
                    JOIN   tbl_expense_type et ON et.expense_type_id = ex.expense_type_id
                    JOIN   tbl_employee      e ON e.emp_id           = ex.employee_id
                    {where}
                    ORDER BY ex.inserted_date DESC
                '''
                c.execute(q, params)
                return c.fetchall()

    def get_expenses_paginated(self, where='', params=(), limit=15, offset=0):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                q = f'''
                    SELECT ex.expense_id, et.expense_type, st.sub_expense_type,
                        e.first_name||' '||e.last_name AS emp_name,
                        ex.exp_description, ex.status,
                        ex.approver_comments, ex.final_comments,
                        ex.inserted_date, ex.amount,
                        ex.employee_id,
                        ex.approved_date,
                        ex.expense_date,
                        ex.invoice_path,
                        ex.po_no,
                        ex.bill_status,
                        ex.expense_by
                    FROM tbl_expenses ex
                    JOIN tbl_expense_type et ON et.expense_type_id = ex.expense_type_id
                    LEFT JOIN tbl_sub_expense_type st ON st.sub_expense_type_id = ex.sub_expense_type_id
                    JOIN tbl_employee e ON e.emp_id = ex.employee_id
                    {where}
                    ORDER BY ex.inserted_date DESC
                    LIMIT %s OFFSET %s
                '''
                c.execute(q, (*params, limit, offset))
                return c.fetchall()

    def count_expenses(self, where='', params=()):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                q = f'''
                    SELECT COUNT(*)
                    FROM tbl_expenses ex
                    JOIN tbl_expense_type et ON et.expense_type_id = ex.expense_type_id
                    JOIN tbl_employee e ON e.emp_id = ex.employee_id
                    {where}
                '''
                c.execute(q, params)
                return c.fetchone()[0]

    def get_expense_by_id(self, exp_id):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                q = '''
                    SELECT ex.expense_id, et.expense_type, st.sub_expense_type,
                        e.first_name||' '||e.last_name AS emp_name,
                        ex.exp_description, ex.status,
                        ex.approver_comments, ex.final_comments,
                        ex.inserted_date, ex.amount,
                        ex.employee_id,
                        ex.approved_date,
                        ex.po_no,
                        ex.bill_status,
                        ex.expense_by
                    FROM tbl_expenses ex
                    JOIN tbl_expense_type et ON et.expense_type_id = ex.expense_type_id
                    LEFT JOIN tbl_sub_expense_type st ON st.sub_expense_type_id = ex.sub_expense_type_id
                    JOIN tbl_employee e ON e.emp_id = ex.employee_id
                    WHERE ex.expense_id = %s
                '''
                c.execute(q, (exp_id,))
                return c.fetchone()

    def update_expense_status(self, exp_id, status, approver_comments='', manager_id=None, approved_by=None):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                if status == 'approved':
                    utc_now = datetime.now(pytz.utc).isoformat()
                    c.execute('''
                        UPDATE tbl_expenses
                        SET status=%s, approver_comments=%s, manager_id=%s, approved_by=%s, approved_date=%s
                        WHERE expense_id=%s
                    ''', (status, approver_comments, manager_id, approved_by, utc_now, exp_id))
                else:
                    c.execute('''
                        UPDATE tbl_expenses
                        SET status=%s, approver_comments=%s, manager_id=%s, approved_by=%s
                        WHERE expense_id=%s
                    ''', (status, approver_comments, manager_id, approved_by, exp_id))

    # ========== SUB EXPENSE TYPE ================================================
    def add_sub_expense_type(self, expense_type_id, sub_expense_type):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                try:
                    c.execute('INSERT INTO tbl_sub_expense_type (expense_type_id, sub_expense_type) VALUES (%s, %s)',
                            (expense_type_id, sub_expense_type))
                    return True, 'Sub-expense type added successfully.'
                except psycopg2.IntegrityError:
                    return False, 'This sub-expense type already exists for this expense type.'

    def get_sub_expense_types(self, expense_type_id=None):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                if expense_type_id:
                    c.execute('''
                        SELECT st.sub_expense_type_id, st.sub_expense_type, st.expense_type_id, et.expense_type
                        FROM tbl_sub_expense_type st
                        JOIN tbl_expense_type et ON st.expense_type_id = et.expense_type_id
                        WHERE st.expense_type_id = %s
                        ORDER BY st.sub_expense_type
                    ''', (expense_type_id,))
                    return c.fetchall()
                else:
                    c.execute('''
                        SELECT st.sub_expense_type_id, st.sub_expense_type, st.expense_type_id, et.expense_type
                        FROM tbl_sub_expense_type st
                        JOIN tbl_expense_type et ON st.expense_type_id = et.expense_type_id
                        ORDER BY et.expense_type, st.sub_expense_type
                    ''')
                    return c.fetchall()

    def update_sub_expense_type(self, sub_et_id, sub_expense_type):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                try:
                    c.execute('UPDATE tbl_sub_expense_type SET sub_expense_type = %s WHERE sub_expense_type_id = %s',
                            (sub_expense_type, sub_et_id))
                    return c.rowcount > 0
                except psycopg2.IntegrityError:
                    return False

    def delete_sub_expense_type(self, sub_et_id):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('DELETE FROM tbl_sub_expense_type WHERE sub_expense_type_id = %s', (sub_et_id,))
