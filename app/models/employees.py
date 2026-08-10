"""Employee, registration-request and employee-profile data-access methods
(moved verbatim from database.py)."""
import psycopg2
import psycopg2.extras


class EmployeeMixin:
    def add_employee(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        hashed_password = self.hash_password(data['password'])
        cursor.execute('''
            INSERT INTO tbl_employee
            (first_name, last_name, gender, dob, address, phone_no, email, password, status, emp_type, department)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING emp_id
        ''', (data['first_name'], data['last_name'], data['gender'], data['dob'],
              data['address'], data['phone_no'], data['email'], hashed_password,
              data['status'], data['emp_type'], data.get('department')))

        emmpp = cursor.fetchone()[0]
        # Automatically insert profile row
        cursor.execute("SELECT COUNT(*) FROM TblEmployeeProfile WHERE EmployeeId = %s", (emmpp,))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO TblEmployeeProfile (EmployeeId, EmgUpdatedByEmp)
                VALUES (%s, 0)
            ''', (emmpp,))
        conn.commit()
        conn.close()
        return emmpp

    def update_employee(self, emp_id, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        if data['password']:
            hashed_password = self.hash_password(data['password'])
        else:
            cursor.execute('SELECT password FROM tbl_employee WHERE emp_id = %s', (emp_id,))
            hashed_password = cursor.fetchone()[0]

        cursor.execute('''
            UPDATE tbl_employee
            SET first_name = %s, last_name = %s, gender = %s, dob = %s, address = %s,
                phone_no = %s, email = %s, password = %s, status = %s, emp_type = %s, department = %s
            WHERE emp_id = %s
        ''', (data['first_name'], data['last_name'], data['gender'], data['dob'],
              data['address'], data['phone_no'], data['email'], hashed_password,
              data['status'], data['emp_type'], data.get('department'), emp_id))

        conn.commit()
        conn.close()

    def delete_employee(self, emp_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check for associated tasks
        cursor.execute('SELECT COUNT(*) FROM tbl_task WHERE emp_id = %s', (emp_id,))
        task_count = cursor.fetchone()[0]

        if task_count > 0:
            conn.close()
            raise Exception('Cannot delete employee with assigned tasks.')

        cursor.execute('DELETE FROM tbl_employee WHERE emp_id = %s', (emp_id,))
        conn.commit()
        conn.close()

    def get_employee(self, emp_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT emp_id, first_name, last_name, gender, dob, address, phone_no, email, status, emp_type, department, password
            FROM tbl_employee
            WHERE emp_id = %s
        ''', (emp_id,))

        employee = cursor.fetchone()
        conn.close()
        return employee

    def get_employees(self, status_filter='all'):
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT emp_id, first_name, last_name, gender, dob, address, phone_no, email, status, emp_type, inserted_date, password, department
            FROM tbl_employee
        '''
        params = []

        if status_filter != 'all':
            query += ' WHERE status = %s'
            params.append(status_filter)

        query += ' ORDER BY inserted_date DESC'

        cursor.execute(query, params)
        employees = cursor.fetchall()
        conn.close()
        return employees

    # Registration request helper methods
    def add_registration_request(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tbl_registration_requests (
                first_name, last_name, gender, dob, address, phone_no, email, password, department, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING request_id
        ''', (data['first_name'], data['last_name'], data['gender'], data['dob'],
              data['address'], data['phone_no'], data['email'], data['password'],
              data['department']))

        req_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return req_id

    def get_registration_requests(self, status='pending'):
        conn = self.get_connection()
        cursor = conn.cursor()

        if status == 'all':
            cursor.execute('''
                SELECT request_id, first_name, last_name, phone_no, department, email, status, inserted_date
                FROM tbl_registration_requests
                ORDER BY inserted_date DESC
            ''')
        else:
            cursor.execute('''
                SELECT request_id, first_name, last_name, phone_no, department, email, status, inserted_date
                FROM tbl_registration_requests
                WHERE status = %s
                ORDER BY inserted_date DESC
            ''', (status,))

        requests = cursor.fetchall()
        conn.close()
        return requests

    def get_registration_request(self, request_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT request_id, first_name, last_name, gender, dob, address, phone_no, email, password, department, status, inserted_date
            FROM tbl_registration_requests
            WHERE request_id = %s
        ''', (request_id,))

        req = cursor.fetchone()
        conn.close()
        return req

    def update_registration_status(self, request_id, status):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tbl_registration_requests
            SET status = %s
            WHERE request_id = %s
        ''', (status, request_id))

        conn.commit()
        conn.close()

    # ---------- EMPLOYEE PROFILE ----------
    def get_employee_profile(self, emp_id):
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM TblEmployeeProfile WHERE EmployeeId = %s", (emp_id,))
            row = cursor.fetchone()
            return dict(row) if row else None  # Return dict for safer access

    def add_employee_profile(self, data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO TblEmployeeProfile (
                    EmployeeId, UANNo, PANNO, AadharNo, BankName, BranchName, ACNo, IFSCode,
                    Designation, EmgContact, ReportingMng, DOJ, PrgLng, FrmWrk
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['EmployeeId'], data['UANNo'], data['PANNO'], data['AadharNo'],
                data['BankName'], data['BranchName'], data['ACNo'], data['IFSCode'],
                data['Designation'], data['EmgContact'], data['ReportingMng'],
                data['DOJ'], data['PrgLng'], data['FrmWrk']
            ))

    def update_employee_profile(self, emp_id, data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE TblEmployeeProfile SET
                    UANNo=%s, PANNO=%s, AadharNo=%s, BankName=%s, BranchName=%s, ACNo=%s, IFSCode=%s,
                    Designation=%s, EmgContact=%s, ReportingMng=%s, DOJ=%s, PrgLng=%s, FrmWrk=%s
                WHERE EmployeeId=%s
            ''', (
                data['UANNo'], data['PANNO'], data['AadharNo'], data['BankName'],
                data['BranchName'], data['ACNo'], data['IFSCode'], data['Designation'],
                data['EmgContact'], data['ReportingMng'], data['DOJ'], data['PrgLng'],
                data['FrmWrk'], emp_id
            ))

    def update_employee_password_and_emgcontact(self, emp_id, new_password, emg_contact):
        new_password = new_password.strip() if new_password else None
        emg_contact = emg_contact.strip() if emg_contact else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if profile exists, if not, create it
            cursor.execute("SELECT COUNT(*) FROM TblEmployeeProfile WHERE EmployeeId = %s", (emp_id,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO TblEmployeeProfile (EmployeeId, EmgUpdatedByEmp) VALUES (%s, 0)", (emp_id,))
            
            if new_password and emg_contact:
                hashed = self.hash_password(new_password)
                cursor.execute('UPDATE tbl_employee SET password = %s WHERE emp_id = %s', (hashed, emp_id))
                cursor.execute('UPDATE TblEmployeeProfile SET EmgContact = %s WHERE EmployeeId = %s', (emg_contact, emp_id))
                conn.commit()
                return "Emergency contact and password updated successfully."
            elif new_password:
                hashed = self.hash_password(new_password)
                cursor.execute('UPDATE tbl_employee SET password = %s WHERE emp_id = %s', (hashed, emp_id))
                conn.commit()
                return "Password updated successfully."
            elif emg_contact:
                cursor.execute('UPDATE TblEmployeeProfile SET EmgContact = %s WHERE EmployeeId = %s', (emg_contact, emp_id))
                conn.commit()
                return "Emergency contact updated successfully."
            else:
                return "No changes made."

    def update_employee_emg_contact_once(self, emp_id, new_emg):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE TblEmployeeProfile
                SET EmgContact = %s, EmgUpdatedByEmp = 1
                WHERE EmployeeId = %s AND EmgUpdatedByEmp = 0
            ''', (new_emg, emp_id))
            return cursor.rowcount > 0
