"""Bulk delete (admin quick-delete) data-access methods
(moved verbatim from database.py)."""


class AdminMixin:
    def delete_all_employees(self):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM tbl_employee WHERE emp_type != 'admin'")

    def delete_all_tasks(self):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM tbl_task_details')
                cursor.execute('DELETE FROM tbl_task')

    def delete_all_leave_types(self):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM tbl_leave_type')

    def delete_all_expense_types(self):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM tbl_expense_type')

    def delete_all_sub_expense_types(self):
        with self.get_connection() as c:
            with c.cursor() as cursor:
                cursor.execute('DELETE FROM tbl_sub_expense_type')
