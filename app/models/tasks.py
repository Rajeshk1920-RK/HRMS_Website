"""Task, task-detail, status-master, analytics and daily-task data-access
methods (moved verbatim from database.py).

NOTE: the task/employee status-master methods were defined twice in the
original database.py; both copies are preserved as-is (the later definition
wins, exactly as before) to keep behaviour byte-identical.
"""
import sqlite3


class TaskMixin:
    # ========== TASK-MANAGEMENT-USING-PYTHON-AND-DATABASE======================
    def add_task(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tbl_task
            (project_id, emp_id, task_desc, priority, status, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['project_id'], data['emp_id'], data['task_desc'],
              data['priority'], data['status'], data['start_date'], data['end_date']))

        conn.commit()
        conn.close()

    def update_task(self, task_id, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_task
            SET project_id = ?, emp_id = ?, task_desc = ?, priority = ?,
                status = ?, start_date = ?, end_date = ?
            WHERE task_id = ?
        ''', (data['project_id'], data['emp_id'], data['task_desc'],
              data['priority'], data['status'], data['start_date'], data['end_date'], task_id))

        conn.commit()
        conn.close()

    def delete_task(self, task_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Delete associated task details
        cursor.execute('DELETE FROM tbl_task_details WHERE task_id = ?', (task_id,))
        cursor.execute('DELETE FROM tbl_task WHERE task_id = ?', (task_id,))

        conn.commit()
        conn.close()

    def get_task(self, task_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT task_id, task_desc, project_id, emp_id, priority, status, start_date, end_date
            FROM tbl_task
            WHERE task_id = ?
        ''', (task_id,))

        task = cursor.fetchone()
        conn.close()
        return task

    def get_tasks_by_employee(self, emp_id, status_filter='all', project_filter='', search_query=''):
            conn = self.get_connection()
            cursor = conn.cursor()

            query = '''
                SELECT t.task_id, t.task_desc, t.priority, t.status, t.start_date, t.end_date,
                    p.project_name
                FROM tbl_task t
                JOIN tbl_project p ON t.project_id = p.project_id
                WHERE t.emp_id = ?
            '''
            params = [emp_id]

            if status_filter != 'all' and status_filter:
                query += ' AND t.status = ?'
                params.append(status_filter)

            if project_filter:
                query += ' AND p.project_name = ?'
                params.append(project_filter)

            if search_query:
                query += ' AND (t.task_desc LIKE ? OR p.project_name LIKE ?)'
                search_term = f'%{search_query}%'
                params.extend([search_term, search_term])

            query += ' ORDER BY t.priority DESC, t.start_date'

            cursor.execute(query, params)
            tasks = cursor.fetchall()
            conn.close()
            return tasks

    def get_all_tasks_with_details_paginated(self, page, page_size, project_filter='', status_filter='', employee_filter='', search_query=''):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Build the base query
        query = '''
            SELECT t.task_id, t.task_desc, t.priority, t.status, t.start_date, t.end_date,
                   p.project_name, e.first_name, e.last_name
            FROM tbl_task t
            JOIN tbl_project p ON t.project_id = p.project_id
            JOIN tbl_employee e ON t.emp_id = e.emp_id
        '''
        count_query = '''
            SELECT COUNT(*)
            FROM tbl_task t
            JOIN tbl_project p ON t.project_id = p.project_id
            JOIN tbl_employee e ON t.emp_id = e.emp_id
        '''
        params = []
        conditions = []

        # Apply filters
        if project_filter:
            conditions.append('p.project_name = ?')
            params.append(project_filter)
        if status_filter:
            conditions.append('t.status = ?')
            params.append(status_filter)
        if employee_filter:
            conditions.append("e.first_name || ' ' || e.last_name = ?")
            params.append(employee_filter)
        if search_query:
            conditions.append("(t.task_desc LIKE ? OR p.project_name LIKE ? OR (e.first_name || ' ' || e.last_name) LIKE ?)")
            search_term = f'%{search_query}%'
            params.extend([search_term, search_term, search_term])

        if conditions:
            condition_str = ' WHERE ' + ' AND '.join(conditions)
            query += condition_str
            count_query += condition_str

        # Add sorting and pagination
        query += ' ORDER BY t.inserted_date DESC LIMIT ? OFFSET ?'
        params.extend([page_size, (page - 1) * page_size])

        # Execute count query
        cursor.execute(count_query, params[:-2] if params[:-2] else [])
        total_tasks = cursor.fetchone()[0]

        # Execute paginated query
        cursor.execute(query, params)
        tasks = cursor.fetchall()

        conn.close()
        return tasks, total_tasks

    def has_task_detail_today(self, task_id, emp_id):
        # Jira-like tracking: Allow multiple task details/updates per day
        return False

    def add_task_detail(self, task_id, desc, status, emp_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Verify task belongs to employee
        cursor.execute('SELECT emp_id FROM tbl_task WHERE task_id = ?', (task_id,))
        task = cursor.fetchone()
        if not task or task[0] != emp_id:
            conn.close()
            raise Exception('Task does not belong to this employee.')

        cursor.execute('''
            INSERT INTO tbl_task_details (task_id, desc, status)
            VALUES (?, ?, ?)
        ''', (task_id, desc, status))

        # Update task status based on the new detail
        if status == 'complete':
            # Check if all task details are now complete
            cursor.execute('''
                SELECT COUNT(*) FROM tbl_task_details
                WHERE task_id = ? AND status != 'complete'
            ''', (task_id,))
            incomplete_count = cursor.fetchone()[0]
            if incomplete_count == 0:
                # All details are complete, set task to completed
                cursor.execute('''
                    UPDATE tbl_task
                    SET status = ?, end_date = DATE('now')
                    WHERE task_id = ?
                ''', ('completed', task_id))
            else:
                # There are still incomplete details, set task to incomplete and clear end_date
                cursor.execute('''
                    UPDATE tbl_task
                    SET status = ?, end_date = NULL
                    WHERE task_id = ?
                ''', ('incomplete', task_id))
        elif status == 'incomplete':
            # Detail is incomplete, set task to incomplete and clear end_date
            cursor.execute('''
                UPDATE tbl_task
                SET status = ?, end_date = NULL
                WHERE task_id = ?
            ''', ('incomplete', task_id))
        else:
            # Unexpected status value, default to incomplete and clear end_date
            cursor.execute('''
                UPDATE tbl_task
                SET status = ?, end_date = NULL
                WHERE task_id = ?
            ''', ('incomplete', task_id))

        conn.commit()
        conn.close()

    def get_task_details_by_employee(self, task_id, emp_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT td.detail_id, td.desc, td.inserted_date, td.status
            FROM tbl_task_details td
            JOIN tbl_task t ON td.task_id = t.task_id
            WHERE td.task_id = ? AND t.emp_id = ?
            ORDER BY td.inserted_date DESC
        ''', (task_id, emp_id))

        details = cursor.fetchall()
        conn.close()
        return details

    def get_task_detail(self, detail_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT td.detail_id, td.task_id, td.desc, td.inserted_date, td.status
            FROM tbl_task_details td
            WHERE td.detail_id = ?
        ''', (detail_id,))

        detail = cursor.fetchone()
        conn.close()
        return detail

    def get_task_details(self, task_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT detail_id, desc, inserted_date, status
            FROM tbl_task_details
            WHERE task_id = ?
            ORDER BY inserted_date DESC
        ''', (task_id,))

        details = cursor.fetchall()
        conn.close()
        return details


    def verify_task_detail_owner(self, detail_id, emp_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*)
            FROM tbl_task_details td
            JOIN tbl_task t ON td.task_id = t.task_id
            WHERE td.detail_id = ? AND t.emp_id = ?
        ''', (detail_id, emp_id))

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def update_task_detail(self, detail_id, desc, status):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_task_details
            SET desc = ?, status = ?, inserted_date = CURRENT_TIMESTAMP
            WHERE detail_id = ?
        ''', (desc, status, detail_id))

        # Get the task_id for this detail
        cursor.execute('SELECT task_id FROM tbl_task_details WHERE detail_id = ?', (detail_id,))
        task_row = cursor.fetchone()
        if task_row:
            task_id = task_row[0]

            # Update task status based on all task details
            if status == 'complete':
                # Check if all task details are now complete
                cursor.execute('''
                    SELECT COUNT(*) FROM tbl_task_details
                    WHERE task_id = ? AND status != 'complete'
                ''', (task_id,))
                incomplete_count = cursor.fetchone()[0]
                if incomplete_count == 0:
                    # All details are complete, set task to completed
                    cursor.execute('''
                        UPDATE tbl_task
                        SET status = ?, end_date = DATE('now')
                        WHERE task_id = ?
                    ''', ('completed', task_id))
                else:
                    # There are still incomplete details, set task to incomplete and clear end_date
                    cursor.execute('''
                        UPDATE tbl_task
                        SET status = ?, end_date = NULL
                        WHERE task_id = ?
                    ''', ('incomplete', task_id))
            else:
                # Detail is incomplete, set task to incomplete and clear end_date
                cursor.execute('''
                    UPDATE tbl_task
                    SET status = ?, end_date = NULL
                    WHERE task_id = ?
                ''', ('incomplete', task_id))

        conn.commit()
        conn.close()

    # ---------- TASK STATUS MASTER ----------
    def get_task_statuses(self):
        with self.get_connection() as c:
            return c.execute('SELECT status_id, name, description, color_class FROM tbl_task_status_master ORDER BY name').fetchall()

    def add_task_status(self, name, description, color_class):
        try:
            with self.get_connection() as c:
                c.execute('INSERT INTO tbl_task_status_master (name, description, color_class) VALUES (?, ?, ?)',
                          (name, description, color_class))
            return True, 'Task status added successfully.'
        except sqlite3.IntegrityError:
            return False, 'This task status already exists.'

    def update_task_status(self, status_id, name, description, color_class):
        try:
            with self.get_connection() as c:
                c.execute('UPDATE tbl_task_status_master SET name = ?, description = ?, color_class = ? WHERE status_id = ?',
                          (name, description, color_class, status_id))
            return True, 'Task status updated successfully.'
        except sqlite3.IntegrityError:
            return False, 'This task status already exists.'

    def delete_task_status(self, status_id):
        with self.get_connection() as c:
            c.execute('DELETE FROM tbl_task_status_master WHERE status_id = ?', (status_id,))
        return True

    # ---------- EMPLOYEE STATUS MASTER ----------
    def get_employee_statuses(self):
        with self.get_connection() as c:
            return c.execute('SELECT status_id, name, description, color_class FROM tbl_employee_status_master ORDER BY name').fetchall()

    def add_employee_status(self, name, description, color_class):
        try:
            with self.get_connection() as c:
                c.execute('INSERT INTO tbl_employee_status_master (name, description, color_class) VALUES (?, ?, ?)',
                          (name, description, color_class))
            return True, 'Employee status added successfully.'
        except sqlite3.IntegrityError:
            return False, 'This employee status already exists.'

    def update_employee_status(self, status_id, name, description, color_class):
        try:
            with self.get_connection() as c:
                c.execute('UPDATE tbl_employee_status_master SET name = ?, description = ?, color_class = ? WHERE status_id = ?',
                          (name, description, color_class, status_id))
            return True, 'Employee status updated successfully.'
        except sqlite3.IntegrityError:
            return False, 'This employee status already exists.'

    def delete_employee_status(self, status_id):
        with self.get_connection() as c:
            c.execute('DELETE FROM tbl_employee_status_master WHERE status_id = ?', (status_id,))
        return True

    # ---------- TASK STATUS MASTER ----------
    def get_task_statuses(self):
        with self.get_connection() as c:
            return c.execute('SELECT status_id, name, description, color_class FROM tbl_task_status_master ORDER BY name').fetchall()

    def add_task_status(self, name, description, color_class):
        try:
            with self.get_connection() as c:
                c.execute('INSERT INTO tbl_task_status_master (name, description, color_class) VALUES (?, ?, ?)',
                          (name, description, color_class))
            return True, 'Task status added successfully.'
        except sqlite3.IntegrityError:
            return False, 'This task status already exists.'

    def update_task_status(self, status_id, name, description, color_class):
        try:
            with self.get_connection() as c:
                c.execute('UPDATE tbl_task_status_master SET name = ?, description = ?, color_class = ? WHERE status_id = ?',
                          (name, description, color_class, status_id))
            return True, 'Task status updated successfully.'
        except sqlite3.IntegrityError:
            return False, 'This task status already exists.'

    def delete_task_status(self, status_id):
        with self.get_connection() as c:
            c.execute('DELETE FROM tbl_task_status_master WHERE status_id = ?', (status_id,))
        return True

    # ---------- EMPLOYEE STATUS MASTER ----------
    def get_employee_statuses(self):
        with self.get_connection() as c:
            return c.execute('SELECT status_id, name, description, color_class FROM tbl_employee_status_master ORDER BY name').fetchall()

    def add_employee_status(self, name, description, color_class):
        try:
            with self.get_connection() as c:
                c.execute('INSERT INTO tbl_employee_status_master (name, description, color_class) VALUES (?, ?, ?)',
                          (name, description, color_class))
            return True, 'Employee status added successfully.'
        except sqlite3.IntegrityError:
            return False, 'This employee status already exists.'

    def update_employee_status(self, status_id, name, description, color_class):
        try:
            with self.get_connection() as c:
                c.execute('UPDATE tbl_employee_status_master SET name = ?, description = ?, color_class = ? WHERE status_id = ?',
                          (name, description, color_class, status_id))
            return True, 'Employee status updated successfully.'
        except sqlite3.IntegrityError:
            return False, 'This employee status already exists.'

    def delete_employee_status(self, status_id):
        with self.get_connection() as c:
            c.execute('DELETE FROM tbl_employee_status_master WHERE status_id = ?', (status_id,))
        return True

    # ========== JIRA-LIKE TRACKING & REPORTS ====================================

    def update_task_status_only(self, task_id, status):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tbl_task
            SET status = ?
            WHERE task_id = ?
        ''', (status, task_id))
        if status == 'completed':
            cursor.execute('''
                UPDATE tbl_task
                SET end_date = DATE('now')
                WHERE task_id = ?
            ''', (task_id,))
        conn.commit()
        conn.close()

    def get_recent_task_activities(self, limit=50, emp_id=None, project_filter='', status_filter='', employee_filter='', search_query=''):
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT td.detail_id, td.task_id, td.desc, td.inserted_date, td.status,
                   t.task_desc, p.project_name, e.first_name, e.last_name
            FROM tbl_task_details td
            JOIN tbl_task t ON td.task_id = t.task_id
            JOIN tbl_project p ON t.project_id = p.project_id
            JOIN tbl_employee e ON t.emp_id = e.emp_id
        '''
        conditions = []
        params = []

        if emp_id:
            conditions.append('t.emp_id = ?')
            params.append(emp_id)
        if project_filter:
            conditions.append('p.project_name = ?')
            params.append(project_filter)
        if status_filter:
            # task status
            conditions.append('t.status = ?')
            params.append(status_filter)
        if employee_filter:
            conditions.append("e.first_name || ' ' || e.last_name = ?")
            params.append(employee_filter)
        if search_query:
            conditions.append("(td.desc LIKE ? OR t.task_desc LIKE ? OR p.project_name LIKE ? OR (e.first_name || ' ' || e.last_name) LIKE ?)")
            search_term = f'%{search_query}%'
            params.extend([search_term, search_term, search_term, search_term])

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' ORDER BY td.inserted_date DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        data = cursor.fetchall()
        conn.close()
        return data

    def get_admin_task_status_counts(self, project_filter='', employee_filter='', search_query=''):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''
            SELECT t.status, COUNT(*)
            FROM tbl_task t
            JOIN tbl_project p ON t.project_id = p.project_id
            JOIN tbl_employee e ON t.emp_id = e.emp_id
        '''
        conditions = []
        params = []
        if project_filter:
            conditions.append('p.project_name = ?')
            params.append(project_filter)
        if employee_filter:
            conditions.append("e.first_name || ' ' || e.last_name = ?")
            params.append(employee_filter)
        if search_query:
            conditions.append("(t.task_desc LIKE ? OR p.project_name LIKE ? OR (e.first_name || ' ' || e.last_name) LIKE ?)")
            search_term = f'%{search_query}%'
            params.extend([search_term, search_term, search_term])

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' GROUP BY t.status'
        cursor.execute(query, params)
        data = cursor.fetchall()
        conn.close()
        return data

    def get_admin_project_task_counts(self, status_filter='', employee_filter='', search_query=''):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''
            SELECT p.project_name, COUNT(t.task_id)
            FROM tbl_project p
            LEFT JOIN tbl_task t ON p.project_id = t.project_id
            LEFT JOIN tbl_employee e ON t.emp_id = e.emp_id
        '''
        conditions = []
        params = []
        if status_filter:
            conditions.append('t.status = ?')
            params.append(status_filter)
        if employee_filter:
            conditions.append("e.first_name || ' ' || e.last_name = ?")
            params.append(employee_filter)
        if search_query:
            conditions.append("(t.task_desc LIKE ? OR p.project_name LIKE ? OR (e.first_name || ' ' || e.last_name) LIKE ?)")
            search_term = f'%{search_query}%'
            params.extend([search_term, search_term, search_term])

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' GROUP BY p.project_id, p.project_name'
        cursor.execute(query, params)
        data = cursor.fetchall()
        conn.close()
        return data

    def get_admin_employee_task_counts(self, project_filter='', status_filter='', search_query=''):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''
            SELECT e.first_name || ' ' || e.last_name as emp_name, COUNT(t.task_id)
            FROM tbl_employee e
            LEFT JOIN tbl_task t ON e.emp_id = t.emp_id
            LEFT JOIN tbl_project p ON t.project_id = p.project_id
            WHERE e.emp_type = 'emp' AND e.status != 'inactive'
        '''
        params = []
        if project_filter:
            query += ' AND p.project_name = ?'
            params.append(project_filter)
        if status_filter:
            query += ' AND t.status = ?'
            params.append(status_filter)
        if search_query:
            query += " AND (t.task_desc LIKE ? OR p.project_name LIKE ? OR (e.first_name || ' ' || e.last_name) LIKE ?)"
            search_term = f'%{search_query}%'
            params.extend([search_term, search_term, search_term])

        query += ' GROUP BY e.emp_id, emp_name'
        cursor.execute(query, params)
        data = cursor.fetchall()
        conn.close()
        return data

    def get_employee_task_status_counts(self, emp_id, project_filter='', search_query=''):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''
            SELECT t.status, COUNT(*)
            FROM tbl_task t
            JOIN tbl_project p ON t.project_id = p.project_id
            WHERE t.emp_id = ?
        '''
        params = [emp_id]
        if project_filter:
            query += ' AND p.project_name = ?'
            params.append(project_filter)
        if search_query:
            query += ' AND (t.task_desc LIKE ? OR p.project_name LIKE ?)'
            search_term = f'%{search_query}%'
            params.extend([search_term, search_term])

        query += ' GROUP BY t.status'
        cursor.execute(query, params)
        data = cursor.fetchall()
        conn.close()
        return data

    # ---------- DAILY TASKS ----------
    def add_daily_task(self, emp_id, title, desc, project_status, task_hours):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tbl_daily_task (emp_id, task_title, task_desc, project_status, task_hours)
            VALUES (?, ?, ?, ?, ?)
        ''', (emp_id, title, desc, project_status, task_hours))
        conn.commit()
        conn.close()

    def get_daily_tasks_by_employee(self, emp_id, start_date=None, end_date=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''
            SELECT daily_task_id, emp_id, task_title, task_desc, project_status, inserted_date, admin_feedback, task_hours
            FROM tbl_daily_task
            WHERE emp_id = ?
        '''
        params = [emp_id]
        if start_date:
            query += ' AND date(inserted_date) >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND date(inserted_date) <= ?'
            params.append(end_date)
        query += ' ORDER BY inserted_date DESC'
        cursor.execute(query, params)
        data = cursor.fetchall()
        conn.close()
        return data

    def get_daily_task(self, daily_task_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT daily_task_id, emp_id, task_title, task_desc, project_status, inserted_date, admin_feedback, task_hours
            FROM tbl_daily_task
            WHERE daily_task_id = ?
        ''', (daily_task_id,))
        data = cursor.fetchone()
        conn.close()
        return data

    def update_daily_task(self, daily_task_id, emp_id, title, desc, project_status, task_hours):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tbl_daily_task
            SET task_title = ?, task_desc = ?, project_status = ?, task_hours = ?
            WHERE daily_task_id = ? AND emp_id = ?
        ''', (title, desc, project_status, task_hours, daily_task_id, emp_id))
        conn.commit()
        conn.close()

    def get_daily_tasks_by_employee_and_date(self, emp_id, task_date):
        """Get daily tasks for a specific employee on a specific date (IST-aware)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT dt.daily_task_id, dt.emp_id, dt.task_title, dt.task_desc, dt.project_status, dt.inserted_date, dt.admin_feedback,
                   e.first_name, e.last_name, dt.task_hours
             FROM tbl_daily_task dt
             JOIN tbl_employee e ON dt.emp_id = e.emp_id
             WHERE dt.emp_id = ? AND date(dt.inserted_date, '+5 hours', '+30 minutes') = ?
             ORDER BY dt.inserted_date DESC
        ''', (emp_id, task_date))
        data = cursor.fetchall()
        conn.close()
        return data

    def get_all_daily_tasks(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT dt.daily_task_id, dt.emp_id, dt.task_title, dt.task_desc, dt.project_status, dt.inserted_date, dt.admin_feedback,
                   e.first_name, e.last_name, dt.task_hours
             FROM tbl_daily_task dt
             JOIN tbl_employee e ON dt.emp_id = e.emp_id
             ORDER BY dt.inserted_date DESC
        ''')
        data = cursor.fetchall()
        conn.close()
        return data

    def update_daily_task_feedback(self, daily_task_id, feedback):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tbl_daily_task
            SET admin_feedback = ?
            WHERE daily_task_id = ?
        ''', (feedback, daily_task_id))
        conn.commit()
        conn.close()

    def delete_daily_task(self, daily_task_id, emp_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM tbl_daily_task
            WHERE daily_task_id = ? AND emp_id = ?
        ''', (daily_task_id, emp_id))
        conn.commit()
        conn.close()
