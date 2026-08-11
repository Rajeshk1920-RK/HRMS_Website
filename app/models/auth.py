"""Authentication data-access methods (moved verbatim from database.py)."""


class AuthMixin:
    def verify_user(self, email, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        hashed_password = self.hash_password(password)

        cursor.execute('''
            SELECT emp_id, first_name, last_name, emp_type, status, profile_photo
            FROM tbl_employee
            WHERE (LOWER(email) = LOWER(%s) OR CAST(emp_id AS TEXT) = %s) AND password = %s AND status != 'inactive'
        ''', (email, email, hashed_password))


        user = cursor.fetchone()
        conn.close()
        return user
