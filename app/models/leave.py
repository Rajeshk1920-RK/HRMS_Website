"""Leave-type, leave-request and leave-summary data-access methods
(moved verbatim from database.py)."""
import psycopg2


class LeaveMixin:
        # ---------- LEAVE TYPE ----------
    def add_leave_type(self, leave_type):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as c:
                    c.execute('INSERT INTO tbl_leave_type (leave_type) VALUES (%s)', (leave_type,))
            return True, 'Leave type added successfully.'
        except psycopg2.IntegrityError:
            return False, 'This leave type already exists.'

    def get_leave_types(self):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('SELECT leave_type_id, leave_type FROM tbl_leave_type ORDER BY leave_type')
                return c.fetchall()

    def update_leave_type(self, lt_id, leave_type):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                try:
                    c.execute('''
                        UPDATE tbl_leave_type
                        SET leave_type = %s
                        WHERE leave_type_id = %s
                    ''', (leave_type, lt_id))
                    return c.rowcount > 0
                except psycopg2.IntegrityError:
                    return False


    def delete_leave_type(self, lt_id):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('DELETE FROM tbl_leave_type WHERE leave_type_id=%s', (lt_id,))

    # ---------- LEAVE REQUESTS --------
    def add_leave_request(self, data):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('''
                    INSERT INTO tbl_leave_request
                    (leave_type_id, employee_id, start_date, end_date,
                    leave_desc, manager_id)
                    VALUES (%s,%s,%s,%s,%s,%s)
                ''', (data['leave_type_id'], data['employee_id'], data['start_date'],
                    data['end_date'], data['leave_desc'], data['manager_id']))

    def get_leave_requests(self, where='', params=()):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                base = '''
                    SELECT lr.request_id, lt.leave_type, e.first_name || ' ' || e.last_name,
                        lr.start_date, lr.end_date, lr.leave_desc,
                        lr.status, lr.comments, lr.inserted_date
                    FROM tbl_leave_request lr
                    JOIN tbl_leave_type lt ON lt.leave_type_id = lr.leave_type_id
                    JOIN tbl_employee e ON e.emp_id = lr.employee_id
                '''

                # Remove any "ORDER" or "LIMIT" in `where` accidentally appended
                if "ORDER BY" in where.upper() or "LIMIT" in where.upper():
                    raise ValueError("Do not include ORDER or LIMIT in 'where' argument")

                query = base + f' {where} ORDER BY lr.inserted_date DESC'
                c.execute(query, params)
                return c.fetchall()

    def update_leave_status(self, req_id, new_status, manager_id, comments=''):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('''
                    UPDATE tbl_leave_request
                    SET status=%s, manager_id=%s, comments=%s, inserted_date=CURRENT_TIMESTAMP
                    WHERE request_id=%s
                ''', (new_status, manager_id, comments, req_id))
    def get_leave_status(self, req_id):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute('SELECT status FROM tbl_leave_request WHERE request_id=%s', (req_id,))
                result = c.fetchone()
                return result[0] if result else None
    def count_leave_requests(self, where='', params=()):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                q = f'''
                    SELECT COUNT(*)
                    FROM tbl_leave_request lr
                    JOIN tbl_leave_type lt ON lt.leave_type_id = lr.leave_type_id
                    JOIN tbl_employee e ON e.emp_id = lr.employee_id
                    {where}
                '''
                c.execute(q, params)
                return c.fetchone()[0]
    def get_leave_requests_paginated(self, where='', params=(), limit=10, offset=0):
        with self.get_connection() as conn:
            with conn.cursor() as c:
                base = '''
                    SELECT lr.request_id, lt.leave_type, e.first_name || ' ' || e.last_name,
                        lr.start_date, lr.end_date, lr.leave_desc,
                        lr.status, lr.comments, lr.inserted_date
                    FROM tbl_leave_request lr
                    JOIN tbl_leave_type lt ON lt.leave_type_id = lr.leave_type_id
                    JOIN tbl_employee e ON e.emp_id = lr.employee_id
                '''

                query = base
                if where:
                    query += f' {where}'

                query += ' ORDER BY lr.inserted_date DESC LIMIT %s OFFSET %s'
                c.execute(query, (*params, limit, offset))
                return c.fetchall()

        # ---------- LEAVE SUMMARY (per employee) --------------------------------
    def get_leave_summary(self, date_from=None, date_to=None, leave_type_id=None):
        """
        Returns (emp_id, emp_name, total_days) for ALL employees,
        even if total_days == 0 (LEFT JOIN).
        """
        where = []
        params = []

        if date_from:
            where.append("lr.start_date >= %s")
            params.append(date_from)
        if date_to:
            where.append("lr.end_date   <= %s")
            params.append(date_to)
        if leave_type_id:
            where.append("lr.leave_type_id = %s")
            params.append(leave_type_id)

        where_sql = " AND ".join(where)
        if where_sql:
            where_sql = "WHERE " + where_sql

        q = f"""
            SELECT  e.emp_id,
                    e.first_name || ' ' || e.last_name AS emp_name,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN lr.start_date IS NULL THEN 0
                                ELSE (lr.end_date::date - lr.start_date::date + 1)
                            END
                        ), 0
                    ) AS total_days
            FROM tbl_employee e
            LEFT JOIN tbl_leave_request lr ON lr.employee_id = e.emp_id
                                             { 'AND ' + where_sql[6:] if where_sql else '' }
            GROUP BY e.emp_id
            ORDER BY e.first_name, e.last_name
        """
        with self.get_connection() as conn:
            with conn.cursor() as c:
                c.execute(q, params)
                return c.fetchall()
