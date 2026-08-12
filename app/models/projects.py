"""Project data-access methods."""
import datetime

class ProjectMixin:
    def add_project(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tbl_project
            (project_name, priority, project_desc, project_status, start_date, end_date,
             project_code, project_type, github_repo, project_manager_id, team_lead_id, created_by, progress_percentage)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            RETURNING project_id
        ''', (data['project_name'], data['priority'], data['project_desc'],
              data['project_status'], data['start_date'], data['end_date'] or None,
              data['project_code'], data['project_type'], data.get('github_repo'),
              data.get('project_manager_id') or None, data.get('team_lead_id') or None,
              data.get('created_by')))

        project_id = cursor.fetchone()[0]

        # Log project activity
        cursor.execute('''
            INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
            VALUES (%s, %s, 'Project Created', %s)
        ''', (project_id, data.get('created_by'), f"Project '{data['project_name']}' created successfully."))

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
                start_date = %s, end_date = %s, project_code = %s, project_type = %s,
                github_repo = %s, project_manager_id = %s, team_lead_id = %s
            WHERE project_id = %s
        ''', (data['project_name'], data['priority'], data['project_desc'],
              data['project_status'], data['start_date'], data['end_date'] or None,
              data['project_code'], data['project_type'], data.get('github_repo'),
              data.get('project_manager_id') or None, data.get('team_lead_id') or None,
              project_id))

        # Log project activity
        user_id = data.get('updated_by') or data.get('created_by')
        if user_id:
            cursor.execute('''
                INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
                VALUES (%s, %s, 'Project Edited', 'Project information updated.')
            ''', (project_id, user_id))

        conn.commit()
        conn.close()

    def archive_project(self, project_id, user_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_project
            SET archived_at = CURRENT_TIMESTAMP
            WHERE project_id = %s
        ''', (project_id,))

        if user_id:
            cursor.execute('''
                INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
                VALUES (%s, %s, 'Project Archived', 'Project moved to archive.')
            ''', (project_id, user_id))

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
            SELECT p.project_id, p.project_name, p.priority, p.project_desc, p.project_status,
                   p.start_date, p.end_date, p.project_code, p.project_type,
                   p.project_manager_id, p.team_lead_id, p.actual_end_date, p.progress_percentage,
                   p.created_by, p.archived_at,
                   m.first_name AS pm_first_name, m.last_name AS pm_last_name,
                   l.first_name AS tl_first_name, l.last_name AS tl_last_name,
                   p.github_repo
            FROM tbl_project p
            LEFT JOIN tbl_employee m ON p.project_manager_id = m.emp_id
            LEFT JOIN tbl_employee l ON p.team_lead_id = l.emp_id
            WHERE p.project_id = %s
        ''', (project_id,))

        project = cursor.fetchone()
        conn.close()
        return project

    def get_projects(self):
        # Default listing (non-archived)
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT p.project_id, p.project_name, p.priority, p.project_desc, p.project_status,
                   p.start_date, p.end_date, p.project_code, p.project_type,
                   p.project_manager_id, p.team_lead_id, p.actual_end_date, p.progress_percentage,
                   p.created_by, p.archived_at,
                   m.first_name AS pm_first_name, m.last_name AS pm_last_name,
                   p.github_repo
            FROM tbl_project p
            LEFT JOIN tbl_employee m ON p.project_manager_id = m.emp_id
            WHERE p.archived_at IS NULL
            ORDER BY p.inserted_date DESC
        ''')

        projects = cursor.fetchall()
        conn.close()
        return projects

    def get_projects_filtered(self, search=None, domain=None, status=None, priority=None, pm_id=None, start_date=None, end_date=None, include_archived=False):
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT p.project_id, p.project_name, p.priority, p.project_desc, p.project_status,
                   p.start_date, p.end_date, p.project_code, p.project_type,
                   p.project_manager_id, p.team_lead_id, p.actual_end_date, p.progress_percentage,
                   p.created_by, p.archived_at,
                   m.first_name AS pm_first_name, m.last_name AS pm_last_name,
                   p.github_repo
            FROM tbl_project p
            LEFT JOIN tbl_employee m ON p.project_manager_id = m.emp_id
            WHERE 1=1
        '''
        params = []

        if not include_archived:
            query += " AND p.archived_at IS NULL"

        if search:
            query += " AND (p.project_name ILIKE %s OR p.project_code ILIKE %s OR m.first_name ILIKE %s OR m.last_name ILIKE %s)"
            search_val = f"%{search}%"
            params.extend([search_val, search_val, search_val, search_val])

        if domain:
            query += " AND p.project_type = %s"
            params.append(domain)

        if status:
            query += " AND p.project_status = %s"
            params.append(status)

        if priority:
            query += " AND p.priority = %s"
            params.append(priority)

        if pm_id:
            query += " AND p.project_manager_id = %s"
            params.append(pm_id)

        if start_date:
            query += " AND p.start_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND p.end_date <= %s"
            params.append(end_date)

        query += " ORDER BY p.inserted_date DESC"

        cursor.execute(query, params)
        projects = cursor.fetchall()
        conn.close()
        return projects

    def get_projects_by_employee(self, employee_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT DISTINCT p.project_id, p.project_name, p.priority, p.project_desc, p.project_status,
                   p.start_date, p.end_date, p.project_code, p.project_type,
                   p.progress_percentage, pm.project_role, p.github_repo
            FROM tbl_project p
            JOIN tbl_project_members pm ON p.project_id = pm.project_id
            WHERE pm.employee_id = %s AND pm.is_active = TRUE AND p.archived_at IS NULL
            ORDER BY p.project_name
        ''', (employee_id,))

        projects = cursor.fetchall()
        conn.close()
        return projects

    # ========== PROJECT MEMBERS ==========
    def get_project_members(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT pm.member_id, pm.project_id, pm.employee_id, pm.project_role, pm.joined_at, pm.is_active,
                   e.first_name, e.last_name, e.email, e.department
            FROM tbl_project_members pm
            JOIN tbl_employee e ON pm.employee_id = e.emp_id
            WHERE pm.project_id = %s AND pm.is_active = TRUE
            ORDER BY e.first_name, e.last_name
        ''', (project_id,))

        members = cursor.fetchall()
        conn.close()
        return members

    def add_project_member(self, project_id, employee_id, role, user_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if already a member (inactive or active)
        cursor.execute('''
            SELECT member_id, is_active FROM tbl_project_members 
            WHERE project_id = %s AND employee_id = %s
        ''', (project_id, employee_id))
        row = cursor.fetchone()

        if row:
            member_id, is_active = row
            cursor.execute('''
                UPDATE tbl_project_members
                SET is_active = TRUE, project_role = %s, joined_at = CURRENT_TIMESTAMP, removed_at = NULL
                WHERE member_id = %s
            ''', (role, member_id))
        else:
            cursor.execute('''
                INSERT INTO tbl_project_members (project_id, employee_id, project_role)
                VALUES (%s, %s, %s)
            ''', (project_id, employee_id, role))

        if user_id:
            cursor.execute("SELECT first_name, last_name FROM tbl_employee WHERE emp_id = %s", (employee_id,))
            emp = cursor.fetchone()
            emp_name = f"{emp[0]} {emp[1]}" if emp else "Employee"
            cursor.execute('''
                INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
                VALUES (%s, %s, 'Employee Added', %s)
            ''', (project_id, user_id, f"Added member {emp_name} as {role}."))

        conn.commit()
        conn.close()

    def remove_project_member(self, project_id, employee_id, user_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_project_members
            SET is_active = FALSE, removed_at = CURRENT_TIMESTAMP
            WHERE project_id = %s AND employee_id = %s
        ''', (project_id, employee_id))

        if user_id:
            cursor.execute("SELECT first_name, last_name FROM tbl_employee WHERE emp_id = %s", (employee_id,))
            emp = cursor.fetchone()
            emp_name = f"{emp[0]} {emp[1]}" if emp else "Employee"
            cursor.execute('''
                INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
                VALUES (%s, %s, 'Employee Removed', %s)
            ''', (project_id, user_id, f"Removed member {emp_name} from project."))

        conn.commit()
        conn.close()

    def update_project_member_role(self, project_id, employee_id, role, user_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_project_members
            SET project_role = %s
            WHERE project_id = %s AND employee_id = %s AND is_active = TRUE
        ''', (role, project_id, employee_id))

        if user_id:
            cursor.execute("SELECT first_name, last_name FROM tbl_employee WHERE emp_id = %s", (employee_id,))
            emp = cursor.fetchone()
            emp_name = f"{emp[0]} {emp[1]}" if emp else "Employee"
            cursor.execute('''
                INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
                VALUES (%s, %s, 'Role Changed', %s)
            ''', (project_id, user_id, f"Changed role of {emp_name} to {role}."))

        conn.commit()
        conn.close()

    # ========== PROJECT MODULES ==========
    def get_project_modules(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT m.module_id, m.project_id, m.name, m.description, m.module_lead_id, m.start_date, m.end_date, m.status,
                   e.first_name, e.last_name
            FROM tbl_project_modules m
            LEFT JOIN tbl_employee e ON m.module_lead_id = e.emp_id
            WHERE m.project_id = %s AND m.status = 'Active'
            ORDER BY m.name
        ''', (project_id,))

        modules = cursor.fetchall()
        conn.close()
        return modules

    def add_project_module(self, project_id, name, description, lead_id, start_date, end_date, user_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tbl_project_modules (project_id, name, description, module_lead_id, start_date, end_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Active')
            RETURNING module_id
        ''', (project_id, name, description, lead_id or None, start_date or None, end_date or None))
        module_id = cursor.fetchone()[0]

        if user_id:
            cursor.execute('''
                INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
                VALUES (%s, %s, 'Module Added', %s)
            ''', (project_id, user_id, f"Added module '{name}'."))

        conn.commit()
        conn.close()
        return module_id

    def update_project_module(self, module_id, name, description, lead_id, start_date, end_date, status, user_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_project_modules
            SET name = %s, description = %s, module_lead_id = %s, start_date = %s, end_date = %s, status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE module_id = %s
            RETURNING project_id
        ''', (name, description, lead_id or None, start_date or None, end_date or None, status, module_id))
        
        project_id = cursor.fetchone()[0]

        if user_id:
            cursor.execute('''
                INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
                VALUES (%s, %s, 'Module Updated', %s)
            ''', (project_id, user_id, f"Updated module '{name}' details."))

        conn.commit()
        conn.close()

    def archive_project_module(self, module_id, user_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_project_modules
            SET status = 'Archived', updated_at = CURRENT_TIMESTAMP
            WHERE module_id = %s
            RETURNING project_id, name
        ''', (module_id,))
        
        project_id, name = cursor.fetchone()

        if user_id:
            cursor.execute('''
                INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
                VALUES (%s, %s, 'Module Archived', %s)
            ''', (project_id, user_id, f"Archived module '{name}'."))

        conn.commit()
        conn.close()

    # ========== PROJECT ACTIVITY ==========
    def log_project_activity(self, project_id, user_id, activity_type, description):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tbl_project_activity (project_id, user_id, activity_type, description)
            VALUES (%s, %s, %s, %s)
        ''', (project_id, user_id, activity_type, description))

        conn.commit()
        conn.close()

    def get_project_activity(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT a.activity_id, a.project_id, a.user_id, a.activity_type, a.description, a.created_at,
                   e.first_name, e.last_name
            FROM tbl_project_activity a
            JOIN tbl_employee e ON a.user_id = e.emp_id
            WHERE a.project_id = %s
            ORDER BY a.created_at DESC
            LIMIT 50
        ''', (project_id,))

        activities = cursor.fetchall()
        conn.close()
        return activities

    # ========== HEALTH & STATS ==========
    def get_project_health(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get project end date
        cursor.execute("SELECT end_date, project_status FROM tbl_project WHERE project_id = %s", (project_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return 'ON TRACK'
        
        end_date, status = row
        if status == 'Completed':
            conn.close()
            return 'ON TRACK'

        current_date = datetime.date.today()

        # Check if project deadline has passed
        if end_date and current_date > end_date:
            conn.close()
            return 'DELAYED'

        # Check for overdue critical tasks
        cursor.execute('''
            SELECT COUNT(*) FROM tbl_task
            WHERE project_id = %s AND status != 'completed' AND priority = 'Critical' AND end_date < %s
        ''', (project_id, current_date))
        critical_overdue = cursor.fetchone()[0]

        if critical_overdue > 0:
            conn.close()
            return 'DELAYED'

        # Check for blocked tasks
        cursor.execute('''
            SELECT COUNT(*) FROM tbl_task
            WHERE project_id = %s AND status = 'blocked'
        ''', (project_id,))
        blocked_tasks = cursor.fetchone()[0]

        # Check for general overdue tasks
        cursor.execute('''
            SELECT COUNT(*) FROM tbl_task
            WHERE project_id = %s AND status != 'completed' AND end_date < %s
        ''', (project_id, current_date))
        overdue_tasks = cursor.fetchone()[0]

        conn.close()

        if overdue_tasks > 3 or blocked_tasks > 1:
            return 'AT RISK'
        
        return 'ON TRACK'

    def update_project_progress(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM tbl_task WHERE project_id = %s", (project_id,))
        total_tasks = cursor.fetchone()[0]

        if total_tasks == 0:
            progress = 0
        else:
            cursor.execute("SELECT COUNT(*) FROM tbl_task WHERE project_id = %s AND status = 'completed'", (project_id,))
            completed_tasks = cursor.fetchone()[0]
            progress = int((completed_tasks / total_tasks) * 100)

        cursor.execute("UPDATE tbl_project SET progress_percentage = %s WHERE project_id = %s", (progress, project_id))
        conn.commit()
        conn.close()

    def get_project_dashboard_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Project KPIs
        cursor.execute("SELECT COUNT(*) FROM tbl_project WHERE archived_at IS NULL")
        total_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tbl_project WHERE project_status = 'Active' AND archived_at IS NULL")
        active_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tbl_project WHERE project_status = 'Completed' AND archived_at IS NULL")
        completed_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tbl_project WHERE project_status = 'On Hold' AND archived_at IS NULL")
        on_hold_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tbl_project WHERE project_status = 'Blocked' AND archived_at IS NULL")
        blocked_projects = cursor.fetchone()[0]

        # Count total tasks and QA pending tasks
        cursor.execute("SELECT COUNT(*) FROM tbl_task")
        total_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tbl_task WHERE status = 'qa_testing'")
        qa_pending_tasks = cursor.fetchone()[0]

        # Calculate At Risk and Delayed projects based on health check
        cursor.execute("SELECT project_id, end_date, project_status FROM tbl_project WHERE archived_at IS NULL")
        projects = cursor.fetchall()
        
        at_risk_projects = 0
        delayed_projects = 0
        current_date = datetime.date.today()

        for pid, end_dt, p_status in projects:
            if p_status == 'Completed':
                continue
            if end_dt and current_date > end_dt:
                delayed_projects += 1
                continue
            
            # Check critical overdue
            cursor.execute("SELECT COUNT(*) FROM tbl_task WHERE project_id = %s AND status != 'completed' AND priority = 'Critical' AND end_date < %s", (pid, current_date))
            if cursor.fetchone()[0] > 0:
                delayed_projects += 1
                continue

            # Check blocked and overdue
            cursor.execute("SELECT COUNT(*) FROM tbl_task WHERE project_id = %s AND status = 'blocked'", (pid,))
            blocked = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tbl_task WHERE project_id = %s AND status != 'completed' AND end_date < %s", (pid, current_date))
            overdue = cursor.fetchone()[0]

            if overdue > 3 or blocked > 1:
                at_risk_projects += 1

        conn.close()

        return {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'on_hold_projects': on_hold_projects,
            'blocked_projects': blocked_projects,
            'at_risk_projects': at_risk_projects,
            'delayed_projects': delayed_projects,
            'total_tasks': total_tasks,
            'qa_pending_tasks': qa_pending_tasks
        }

    def get_tasks_by_project(self, project_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT t.task_id, t.task_desc, t.project_id, t.emp_id, t.priority, t.status,
                   t.start_date, t.end_date, e.first_name, e.last_name,
                   t.title, t.estimated_hours, m.name AS module_name
            FROM tbl_task t
            JOIN tbl_employee e ON t.emp_id = e.emp_id
            LEFT JOIN tbl_project_modules m ON t.module_id = m.module_id
            WHERE t.project_id = %s
            ORDER BY t.inserted_date DESC
        ''', (project_id,))

        tasks = cursor.fetchall()
        conn.close()
        return tasks
