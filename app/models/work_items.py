"""Work item and QA workflow data-access methods."""

class WorkItemMixin:
    def add_work_item(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Auto-generate work_id based on next ID
        cursor.execute("SELECT COALESCE(MAX(work_item_id), 0) + 1 FROM tbl_work_items")
        next_id = cursor.fetchone()[0]
        work_id = f"WI-{next_id:04d}"

        cursor.execute('''
            INSERT INTO tbl_work_items
            (work_id, project_id, employee_id, work_title, description, technical_description, estimated_hours, created_by, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'New')
            RETURNING work_item_id
        ''', (work_id, data['project_id'], data['employee_id'], data['work_title'],
              data.get('description'), data.get('technical_description'),
              data.get('estimated_hours', 0.0), data['created_by']))
        
        work_item_id = cursor.fetchone()[0]
        
        # Add initial log update
        cursor.execute('''
            INSERT INTO tbl_work_details (work_item_id, created_by, description)
            VALUES (%s, %s, 'Work item created in New status.')
        ''', (work_item_id, data['created_by']))

        conn.commit()
        conn.close()
        return work_item_id

    def get_work_item(self, work_item_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT w.work_item_id, w.work_id, w.project_id, w.employee_id, w.work_title,
                   w.description, w.technical_description, w.estimated_hours, w.created_by,
                   w.created_date, w.status, p.project_name, 
                   e.first_name, e.last_name,
                   c.first_name, c.last_name
            FROM tbl_work_items w
            JOIN tbl_project p ON w.project_id = p.project_id
            JOIN tbl_employee e ON w.employee_id = e.emp_id
            JOIN tbl_employee c ON w.created_by = c.emp_id
            WHERE w.work_item_id = %s
        ''', (work_item_id,))

        work_item = cursor.fetchone()
        conn.close()
        return work_item

    def get_work_items(self, project_id=None, employee_id=None, status=None, search=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT w.work_item_id, w.work_id, w.project_id, w.employee_id, w.work_title,
                   w.description, w.technical_description, w.estimated_hours, w.created_by,
                   w.created_date, w.status, p.project_name, e.first_name, e.last_name
            FROM tbl_work_items w
            JOIN tbl_project p ON w.project_id = p.project_id
            JOIN tbl_employee e ON w.employee_id = e.emp_id
            WHERE 1=1
        '''
        params = []

        if project_id:
            query += " AND w.project_id = %s"
            params.append(project_id)
        if employee_id:
            query += " AND w.employee_id = %s"
            params.append(employee_id)
        if status:
            query += " AND w.status = %s"
            params.append(status)
        if search:
            query += " AND (w.work_title ILIKE %s OR w.work_id ILIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        query += " ORDER BY w.created_date DESC"

        cursor.execute(query, params)
        work_items = cursor.fetchall()
        conn.close()
        return work_items

    def update_work_item_status(self, work_item_id, status, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get old status
        cursor.execute("SELECT status FROM tbl_work_items WHERE work_item_id = %s", (work_item_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise Exception("Work item not found.")
        old_status = row[0]

        if old_status == status:
            conn.close()
            return

        # Update status
        cursor.execute('''
            UPDATE tbl_work_items
            SET status = %s
            WHERE work_item_id = %s
        ''', (status, work_item_id))

        # Add history log
        cursor.execute('''
            INSERT INTO tbl_work_details (work_item_id, created_by, description)
            VALUES (%s, %s, %s)
        ''', (work_item_id, user_id, f"Status updated from '{old_status}' to '{status}'."))

        conn.commit()
        conn.close()

    def add_work_item_detail(self, work_item_id, user_id, description):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tbl_work_details (work_item_id, created_by, description)
            VALUES (%s, %s, %s)
        ''', (work_item_id, user_id, description))

        conn.commit()
        conn.close()

    def get_work_item_details(self, work_item_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT d.work_item_details_id, d.work_item_id, d.created_by, d.description, d.created_date_time,
                   e.first_name, e.last_name, e.emp_type
            FROM tbl_work_details d
            JOIN tbl_employee e ON d.created_by = e.emp_id
            WHERE d.work_item_id = %s
            ORDER BY d.created_date_time DESC
        ''', (work_item_id,))

        details = cursor.fetchall()
        conn.close()
        return details

    def submit_qa_result(self, work_item_id, tester_id, result, description):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get work item current status
        cursor.execute("SELECT status FROM tbl_work_items WHERE work_item_id = %s", (work_item_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise Exception("Work item not found.")
        current_status = row[0]

        # Insert tbl_work_qa header
        cursor.execute('''
            INSERT INTO tbl_work_qa (work_item_id, employee_id)
            VALUES (%s, %s)
            RETURNING qa_id
        ''', (work_item_id, tester_id))
        qa_id = cursor.fetchone()[0]

        # Insert tbl_work_qa_details
        cursor.execute('''
            INSERT INTO tbl_work_qa_details (qa_id, status, result, description)
            VALUES (%s, %s, %s, %s)
        ''', (qa_id, current_status, result, description))

        # Update work item status based on result
        next_status = 'UAT' if result == 'PASS' else 'Active'
        cursor.execute('''
            UPDATE tbl_work_items
            SET status = %s
            WHERE work_item_id = %s
        ''', (next_status, work_item_id))

        # Add history log
        cursor.execute('''
            INSERT INTO tbl_work_details (work_item_id, created_by, description)
            VALUES (%s, %s, %s)
        ''', (work_item_id, tester_id, f"QA Result: {result}. Review description: {description}. Status set to '{next_status}'."))

        conn.commit()
        conn.close()

    def get_work_item_qa_history(self, work_item_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT q.qa_id, q.work_item_id, q.employee_id, q.created_date_time,
                   qd.qa_details_id, qd.status, qd.result, qd.description, qd.created_date_time,
                   e.first_name, e.last_name
            FROM tbl_work_qa q
            JOIN tbl_work_qa_details qd ON q.qa_id = qd.qa_id
            JOIN tbl_employee e ON q.employee_id = e.emp_id
            WHERE q.work_item_id = %s
            ORDER BY qd.created_date_time DESC
        ''', (work_item_id,))

        history = cursor.fetchall()
        conn.close()
        return history

    def get_project_dashboard_metrics(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Total Tasks
        cursor.execute("SELECT COUNT(*) FROM tbl_work_items WHERE project_id = %s", (project_id,))
        total_tasks = cursor.fetchone()[0]

        # 2. Total Hours
        cursor.execute("SELECT COALESCE(SUM(estimated_hours), 0.00) FROM tbl_work_items WHERE project_id = %s", (project_id,))
        total_hours = float(cursor.fetchone()[0])

        # 3. 1st QA Passed
        # Meaning: Work items where the very first QA run was PASS (i.e. zero fails in its lifecycle, but has at least one pass)
        cursor.execute('''
            SELECT COUNT(DISTINCT w.work_item_id)
            FROM tbl_work_items w
            JOIN tbl_work_qa q ON w.work_item_id = q.work_item_id
            WHERE w.project_id = %s
              AND w.work_item_id NOT IN (
                  SELECT DISTINCT q2.work_item_id
                  FROM tbl_work_qa q2
                  JOIN tbl_work_qa_details qd2 ON q2.qa_id = qd2.qa_id
                  WHERE qd2.result = 'FAIL'
              )
        ''', (project_id,))
        first_qa_passed = cursor.fetchone()[0]

        # 4. QA Failed
        # Meaning: Total failed QA attempts (cumulative fails)
        cursor.execute('''
            SELECT COUNT(*)
            FROM tbl_work_qa q
            JOIN tbl_work_qa_details qd ON q.qa_id = qd.qa_id
            JOIN tbl_work_items w ON q.work_item_id = w.work_item_id
            WHERE w.project_id = %s AND qd.result = 'FAIL'
        ''', (project_id,))
        qa_failed = cursor.fetchone()[0]

        conn.close()
        return {
            'total_tasks': total_tasks,
            'total_hours': total_hours,
            'first_qa_passed': first_qa_passed,
            'qa_failed': qa_failed
        }
