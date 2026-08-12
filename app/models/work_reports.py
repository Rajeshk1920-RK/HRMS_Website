"""Work reports data-access methods."""
import datetime

class WorkReportMixin:
    def add_work_report(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tbl_work_reports
            (employee_id, project_id, task_id, report_date, hours_worked, work_description,
             progress_percentage, blocker, tomorrow_plan, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING report_id
        ''', (data['employee_id'], data['project_id'], data['task_id'],
              data.get('report_date') or datetime.date.today(), data['hours_worked'],
              data['work_description'], data.get('progress_percentage', 0),
              data.get('blocker'), data.get('tomorrow_plan')))

        report_id = cursor.fetchone()[0]

        # Log work report submitted in project activity
        cursor.execute("SELECT title FROM tbl_task WHERE task_id = %s", (data['task_id'],))
        task_row = cursor.fetchone()
        task_title = task_row[0] if task_row else "Task"

        cursor.execute("SELECT first_name, last_name FROM tbl_employee WHERE emp_id = %s", (data['employee_id'],))
        emp_row = cursor.fetchone()
        emp_name = f"{emp_row[0]} {emp_row[1]}" if emp_row else "Employee"

        cursor.execute('''
            INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
            VALUES (%s, %s, 'Work Report Submitted', %s)
        ''', (data['project_id'], data['employee_id'], f"{emp_name} submitted work report for task '{task_title}' ({data['hours_worked']} hrs, {data.get('progress_percentage', 0)}% progress)."))

        # Update task progress / status if provided
        cursor.execute('''
            UPDATE tbl_task
            SET completed_at = CASE WHEN %s >= 100 THEN CURRENT_TIMESTAMP ELSE completed_at END
            WHERE task_id = %s
        ''', (data.get('progress_percentage', 0), data['task_id']))

        conn.commit()
        conn.close()

        # Recalculate project progress
        self.update_project_progress(data['project_id'])

        return report_id

    def get_work_report(self, report_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT r.report_id, r.employee_id, r.project_id, r.task_id, r.report_date, r.hours_worked,
                   r.work_description, r.progress_percentage, r.blocker, r.tomorrow_plan, r.status, r.submitted_at,
                   p.project_name, t.title AS task_title, e.first_name, e.last_name
            FROM tbl_work_reports r
            JOIN tbl_project p ON r.project_id = p.project_id
            JOIN tbl_task t ON r.task_id = t.task_id
            JOIN tbl_employee e ON r.employee_id = e.emp_id
            WHERE r.report_id = %s
        ''', (report_id,))

        report = cursor.fetchone()
        conn.close()
        return report

    def get_work_reports_by_employee(self, employee_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT r.report_id, r.employee_id, r.project_id, r.task_id, r.report_date, r.hours_worked,
                   r.work_description, r.progress_percentage, r.blocker, r.tomorrow_plan, r.status, r.submitted_at,
                   p.project_name, t.title AS task_title
            FROM tbl_work_reports r
            JOIN tbl_project p ON r.project_id = p.project_id
            JOIN tbl_task t ON r.task_id = t.task_id
            WHERE r.employee_id = %s
            ORDER BY r.report_date DESC, r.submitted_at DESC
        ''', (employee_id,))

        reports = cursor.fetchall()
        conn.close()
        return reports

    def get_all_work_reports(self, employee_id=None, project_id=None, task_id=None, start_date=None, end_date=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT r.report_id, r.employee_id, r.project_id, r.task_id, r.report_date, r.hours_worked,
                   r.work_description, r.progress_percentage, r.blocker, r.tomorrow_plan, r.status, r.submitted_at,
                   p.project_name, t.title AS task_title, e.first_name, e.last_name
            FROM tbl_work_reports r
            JOIN tbl_project p ON r.project_id = p.project_id
            JOIN tbl_task t ON r.task_id = t.task_id
            JOIN tbl_employee e ON r.employee_id = e.emp_id
            WHERE 1=1
        '''
        params = []

        if employee_id:
            query += " AND r.employee_id = %s"
            params.append(employee_id)
        if project_id:
            query += " AND r.project_id = %s"
            params.append(project_id)
        if task_id:
            query += " AND r.task_id = %s"
            params.append(task_id)
        if start_date:
            query += " AND r.report_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND r.report_date <= %s"
            params.append(end_date)

        query += " ORDER BY r.report_date DESC, r.submitted_at DESC"

        cursor.execute(query, params)
        reports = cursor.fetchall()
        conn.close()
        return reports

    def update_work_report(self, report_id, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check lock status
        cursor.execute("SELECT status, project_id, task_id FROM tbl_work_reports WHERE report_id = %s", (report_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise Exception("Work report not found.")
        
        status, project_id, task_id = row
        if status != 'pending':
            conn.close()
            raise Exception("Cannot edit a locked or approved work report.")

        cursor.execute('''
            UPDATE tbl_work_reports
            SET hours_worked = %s, work_description = %s, progress_percentage = %s,
                blocker = %s, tomorrow_plan = %s, report_date = %s, updated_at = CURRENT_TIMESTAMP
            WHERE report_id = %s
        ''', (data['hours_worked'], data['work_description'], data.get('progress_percentage', 0),
              data.get('blocker'), data.get('tomorrow_plan'), data.get('report_date') or datetime.date.today(),
              report_id))

        conn.commit()
        conn.close()

        # Recalculate project progress
        self.update_project_progress(project_id)

    def lock_work_report(self, report_id, status='approved', user_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_work_reports
            SET status = %s
            WHERE report_id = %s
            RETURNING employee_id, project_id, task_id
        ''', (status, report_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise Exception("Work report not found.")

        emp_id, project_id, task_id = row

        if user_id:
            cursor.execute("SELECT first_name, last_name FROM tbl_employee WHERE emp_id = %s", (emp_id,))
            emp = cursor.fetchone()
            emp_name = f"{emp[0]} {emp[1]}" if emp else "Employee"
            cursor.execute("SELECT title FROM tbl_task WHERE task_id = %s", (task_id,))
            task_title = cursor.fetchone()[0]

            cursor.execute('''
                INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
                VALUES (%s, %s, 'Work Report Locked', %s)
            ''', (project_id, user_id, f"Work report by {emp_name} for task '{task_title}' locked/approved."))

        conn.commit()
        conn.close()
