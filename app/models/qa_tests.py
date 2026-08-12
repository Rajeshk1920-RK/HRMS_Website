"""QA testing data-access methods."""
import datetime

class QATestMixin:
    def get_qa_queue(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # QA Queue displays tasks currently in 'qa_testing' or 'in_review' status
        cursor.execute('''
            SELECT t.task_id, t.title, t.task_desc, t.priority, t.status, t.start_date, t.end_date, t.inserted_date,
                   p.project_id, p.project_name, e.emp_id, e.first_name, e.last_name, m.name AS module_name
            FROM tbl_task t
            JOIN tbl_project p ON t.project_id = p.project_id
            JOIN tbl_employee e ON t.emp_id = e.emp_id
            LEFT JOIN tbl_project_modules m ON t.module_id = m.module_id
            WHERE t.status IN ('qa_testing', 'in_review') AND p.archived_at IS NULL
            ORDER BY t.inserted_date DESC
        ''')

        queue = cursor.fetchall()
        conn.close()
        return queue

    def submit_qa_test(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        task_id = data['task_id']
        tester_id = data['tester_id']
        result = data['result'] # 'PASS' or 'FAIL'

        cursor.execute('''
            INSERT INTO tbl_qa_tests
            (task_id, tester_id, test_date, expected_result, actual_result, result, comments)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING qa_test_id
        ''', (task_id, tester_id, data.get('test_date') or datetime.date.today(),
              data.get('expected_result'), data.get('actual_result'), result, data.get('comments')))

        qa_test_id = cursor.fetchone()[0]

        # Get task and employee details to update task state and log activity
        cursor.execute('''
            SELECT t.title, t.project_id, t.emp_id, e.first_name, e.last_name
            FROM tbl_task t
            JOIN tbl_employee e ON t.emp_id = e.emp_id
            WHERE t.task_id = %s
        ''', (task_id,))
        task_row = cursor.fetchone()
        
        if not task_row:
            conn.close()
            raise Exception("Task not found.")
        
        task_title, project_id, developer_id, dev_first, dev_last = task_row
        dev_name = f"{dev_first} {dev_last}"

        # Transition task status
        next_status = 'completed' if result == 'PASS' else 'in_progress'
        completed_at = datetime.datetime.now() if result == 'PASS' else None

        cursor.execute('''
            UPDATE tbl_task
            SET status = %s, completed_at = %s, end_date = CASE WHEN %s = 'PASS' THEN CURRENT_DATE ELSE end_date END
            WHERE task_id = %s
        ''', (next_status, completed_at, result, task_id))

        # Log project activity
        activity_type = 'QA Passed' if result == 'PASS' else 'QA Failed'
        description = f"Task '{task_title}' (Developer: {dev_name}) passed QA review." if result == 'PASS' else f"Task '{task_title}' (Developer: {dev_name}) failed QA review. Returned to In Progress."
        
        cursor.execute('''
            INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
            VALUES (%s, %s, %s, %s)
        ''', (project_id, tester_id, activity_type, description))

        # Add notification for developer
        notif_text = f"Your task '{task_title}' has {result}ed QA testing."
        cursor.execute('''
            INSERT INTO tbl_notifications (user_id, text)
            VALUES (%s, %s)
        ''', (developer_id, notif_text))

        conn.commit()
        conn.close()

        # Update project progress percentage
        self.update_project_progress(project_id)

        return qa_test_id

    def get_qa_history(self, task_id=None, project_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT q.qa_test_id, q.task_id, q.tester_id, q.test_date, q.expected_result, q.actual_result, q.result, q.comments, q.created_at,
                   t.title AS task_title, p.project_name, e.first_name, e.last_name
            FROM tbl_qa_tests q
            JOIN tbl_task t ON q.task_id = t.task_id
            JOIN tbl_project p ON t.project_id = p.project_id
            JOIN tbl_employee e ON q.tester_id = e.emp_id
            WHERE 1=1
        '''
        params = []

        if task_id:
            query += " AND q.task_id = %s"
            params.append(task_id)
        if project_id:
            query += " AND t.project_id = %s"
            params.append(project_id)

        query += " ORDER BY q.created_at DESC"

        cursor.execute(query, params)
        history = cursor.fetchall()
        conn.close()
        return history
