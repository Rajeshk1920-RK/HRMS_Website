"""Project data-access methods (moved verbatim from database.py)."""


class ProjectMixin:
    def add_project(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tbl_project
            (project_name, priority, project_desc, project_status, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING project_id
        ''', (data['project_name'], data['priority'], data['project_desc'],
              data['project_status'], data['start_date'], data['end_date']))

        project_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return project_id

    def add_project_file(self, project_id, file_name, file_path, file_type, file_size):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tbl_project_files
            (project_id, file_name, file_path, file_type, file_size)
            VALUES (%s, %s, %s, %s, %s)
        ''', (project_id, file_name, file_path, file_type, file_size))

        conn.commit()
        conn.close()

    def get_project_files(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT file_id, project_id, file_name, file_path, file_type, file_size, inserted_date
            FROM tbl_project_files
            WHERE project_id = %s
            ORDER BY inserted_date ASC
        ''', (project_id,))

        files = cursor.fetchall()
        conn.close()
        return files

    def get_project_file(self, file_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT file_id, project_id, file_name, file_path, file_type, file_size, inserted_date
            FROM tbl_project_files
            WHERE file_id = %s
        ''', (file_id,))

        file_rec = cursor.fetchone()
        conn.close()
        return file_rec

    def delete_project_file(self, file_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM tbl_project_files WHERE file_id = %s', (file_id,))
        conn.commit()
        conn.close()

    def update_project(self, project_id, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_project
            SET project_name = %s, priority = %s, project_desc = %s, project_status = %s,
                start_date = %s, end_date = %s
            WHERE project_id = %s
        ''', (data['project_name'], data['priority'], data['project_desc'],
              data['project_status'], data['start_date'], data['end_date'], project_id))

        conn.commit()
        conn.close()

    def delete_project(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check for associated tasks
        cursor.execute('SELECT COUNT(*) FROM tbl_task WHERE project_id = %s', (project_id,))
        task_count = cursor.fetchone()[0]

        if task_count > 0:
            conn.close()
            raise Exception('Cannot delete project with assigned tasks.')

        cursor.execute('DELETE FROM tbl_project WHERE project_id = %s', (project_id,))
        conn.commit()
        conn.close()

    def get_project(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT project_id, project_name, priority, project_desc, project_status, start_date, end_date
            FROM tbl_project
            WHERE project_id = %s
        ''', (project_id,))

        project = cursor.fetchone()
        conn.close()
        return project

    def get_projects(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT project_id, project_name, priority, project_desc, project_status, start_date, end_date, inserted_date
            FROM tbl_project
            ORDER BY inserted_date DESC
        ''')

        projects = cursor.fetchall()
        conn.close()
        return projects

    def get_tasks_by_project(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT t.task_id, t.task_desc, t.project_id, t.emp_id, t.priority, t.status,
                   t.start_date, t.end_date, e.first_name, e.last_name
            FROM tbl_task t
            JOIN tbl_employee e ON t.emp_id = e.emp_id
            WHERE t.project_id = %s
            ORDER BY t.inserted_date DESC
        ''', (project_id,))

        tasks = cursor.fetchall()
        conn.close()
        return tasks
