"""Core database base class: connection handling, schema creation, hashing.

Method bodies moved verbatim from the original database.py.
"""
import psycopg2
import psycopg2.extras
import hashlib


class DatabaseBase:
    def __init__(self, dsn='dbname=project_tracking'):
        self.dsn = dsn
        self.init_database()

    def get_connection(self):
        return psycopg2.connect(self.dsn)

    def init_database(self):
        try:
            conn = self.get_connection()
        except Exception as e:
            # Mask credentials in DSN before logging
            masked_dsn = self.dsn
            if "://" in masked_dsn:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(masked_dsn)
                    if parsed.password:
                        netloc = f"{parsed.username}:******@{parsed.hostname}"
                        if parsed.port:
                            netloc += f":{parsed.port}"
                        masked_dsn = parsed._replace(netloc=netloc).geturl()
                except Exception:
                    masked_dsn = "postgresql://******@******"
            else:
                parts = []
                for part in masked_dsn.split():
                    if part.startswith("password="):
                        parts.append("password=******")
                    elif part.startswith("user="):
                        parts.append("user=******")
                    else:
                        parts.append(part)
                masked_dsn = " ".join(parts)
            
            print("\n" + "="*80)
            print("DATABASE CONNECTION ERROR")
            print("="*80)
            print(f"Failed to connect to the database using DSN: {masked_dsn}")
            print(f"Error: {e}")
            print("="*80 + "\n")
            raise e

        cursor = conn.cursor()


        # Create tbl_employee
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_employee (
                emp_id SERIAL PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                gender TEXT NOT NULL,
                dob DATE NOT NULL,
                address TEXT NOT NULL,
                phone_no TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                emp_type TEXT DEFAULT 'emp',
                department TEXT,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create tbl_project
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_project (
                project_id SERIAL PRIMARY KEY,
                project_name TEXT NOT NULL,
                priority TEXT NOT NULL,
                project_desc TEXT,
                project_status TEXT DEFAULT 'active',
                start_date DATE NOT NULL,
                end_date DATE,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create tbl_task
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_task (
                task_id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                emp_id INTEGER NOT NULL,
                task_desc TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                start_date DATE NOT NULL,
                end_date DATE,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES tbl_project (project_id),
                FOREIGN KEY (emp_id) REFERENCES tbl_employee (emp_id)
            )
        ''')

        # Create tbl_task_details
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_task_details (
                detail_id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                "desc" TEXT NOT NULL,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'incomplete',
                FOREIGN KEY (task_id) REFERENCES tbl_task (task_id)
            )
        ''')

        # -- Leave types master -------------------------------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_leave_type (
                leave_type_id SERIAL PRIMARY KEY,
                leave_type     TEXT NOT NULL UNIQUE CHECK (LENGTH(leave_type)<=50),
                inserted_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # -- Leave requests -----------------------------------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_leave_request (
                request_id      SERIAL PRIMARY KEY,
                leave_type_id   INTEGER NOT NULL,
                employee_id     INTEGER NOT NULL,
                start_date      DATE    NOT NULL,
                end_date        DATE    NOT NULL,
                leave_desc      TEXT    CHECK (LENGTH(leave_desc)<=500),
                manager_id      INTEGER,
                comments        TEXT    CHECK (LENGTH(comments)<=200),
                status          TEXT    DEFAULT 'pending',   -- pending/approved/rejected
                inserted_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (leave_type_id) REFERENCES tbl_leave_type(leave_type_id),
                FOREIGN KEY (employee_id)  REFERENCES tbl_employee(emp_id),
                FOREIGN KEY (manager_id)   REFERENCES tbl_employee(emp_id)
            )
        ''')

        # ------------------ Expense types master --------------------------------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_expense_type (
                expense_type_id SERIAL PRIMARY KEY,
                expense_type    TEXT NOT NULL UNIQUE,            -- duplication guard
                inserted_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ------------------ Expenses --------------------------------------------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_expenses (
                expense_id        SERIAL PRIMARY KEY,
                expense_type_id   INTEGER NOT NULL,
                employee_id       INTEGER NOT NULL,
                exp_description   TEXT CHECK (LENGTH(exp_description)<=500),
                manager_id        INTEGER,                      -- who will approve
                approver_comments TEXT CHECK (LENGTH(approver_comments)<=200),
                given_by_id       INTEGER,                      -- who reimbursed / paid
                final_comments    TEXT CHECK (LENGTH(final_comments)<=200),
                status            TEXT  DEFAULT 'pending',      -- pending/approved/rejected
                inserted_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                amount            DOUBLE PRECISION,
                approved_date     TEXT,
                approved_by       INTEGER,
                expense_date      DATE,
                invoice_path      TEXT,

                FOREIGN KEY (expense_type_id) REFERENCES tbl_expense_type(expense_type_id),
                FOREIGN KEY (employee_id)     REFERENCES tbl_employee(emp_id),
                FOREIGN KEY (manager_id)      REFERENCES tbl_employee(emp_id),
                FOREIGN KEY (given_by_id)     REFERENCES tbl_employee(emp_id)
            )
        ''')

        # ------------------ Sub Expense types master --------------------------------
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tbl_sub_expense_type (
            sub_expense_type_id SERIAL PRIMARY KEY,
            expense_type_id INTEGER NOT NULL,
            sub_expense_type TEXT NOT NULL,
            inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (expense_type_id) REFERENCES tbl_expense_type(expense_type_id) ON DELETE CASCADE,
            UNIQUE(expense_type_id, sub_expense_type)
        )
        ''')

        # Add new columns to tbl_expenses (IF NOT EXISTS handles duplicates)
        cursor.execute('ALTER TABLE tbl_expenses ADD COLUMN IF NOT EXISTS sub_expense_type_id INTEGER REFERENCES tbl_sub_expense_type(sub_expense_type_id)')

        cursor.execute('ALTER TABLE tbl_expenses ADD COLUMN IF NOT EXISTS po_no TEXT')

        cursor.execute('ALTER TABLE tbl_expenses ADD COLUMN IF NOT EXISTS bill_status TEXT')

        cursor.execute('ALTER TABLE tbl_expenses ADD COLUMN IF NOT EXISTS expense_by TEXT')

        cursor.execute('ALTER TABLE tbl_employee ADD COLUMN IF NOT EXISTS profile_photo TEXT')

                # ------------------ Wiki Category --------------------------------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS TblWikiCategory (
                CategoryId SERIAL PRIMARY KEY,
                Category   TEXT    NOT NULL,
                CatImg     TEXT,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ------------------ Wiki Page ------------------------------------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS TblWikiPage (
                WikiId       SERIAL PRIMARY KEY,
                CategoryId   INTEGER NOT NULL,
                Title        TEXT    NOT NULL,
                Descri       TEXT,
                InsertedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                RowStatus    INTEGER DEFAULT 0,
                FOREIGN KEY (CategoryId) REFERENCES TblWikiCategory(CategoryId)
            )
        ''')
            # ------------------ Wiki Views --------------------------------------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS TblWikiViews (
                WikiViewId   SERIAL PRIMARY KEY,
                WikiId       INTEGER NOT NULL,
                EmployeeId   INTEGER NOT NULL,
                ViewDateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (WikiId)     REFERENCES TblWikiPage(WikiId),
                FOREIGN KEY (EmployeeId) REFERENCES tbl_employee(emp_id)
            )
        ''')


        conn.commit()

        # Create default admin user if not exists
        cursor.execute("SELECT COUNT(*) FROM tbl_employee WHERE emp_type = 'admin'")
        admin_count = cursor.fetchone()[0]

        if admin_count == 0:
            hashed_password = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute('''
                INSERT INTO tbl_employee
                (first_name, last_name, gender, dob, address, phone_no, email, password, emp_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', ('Admin', 'User', 'Male', '1990-01-01', 'Admin Address', '1234567890',
                  'admin@company.com', hashed_password, 'admin'))
            conn.commit()

        cursor.execute('''
                CREATE TABLE IF NOT EXISTS TblEmployeeProfile (
                    ProfileId SERIAL PRIMARY KEY,
                    EmployeeId INTEGER NOT NULL UNIQUE,
                    UANNo TEXT,
                    PANNO TEXT,
                    AadharNo TEXT,
                    BankName TEXT,
                    BranchName TEXT,
                    ACNo TEXT,
                    IFSCode TEXT,
                    Designation TEXT,
                    EmgContact TEXT,
                    ReportingMng TEXT,
                    DOJ DATE,
                    PrgLng TEXT,
                    FrmWrk TEXT,
                    EmgUpdatedByEmp INTEGER DEFAULT 0,
                    FOREIGN KEY(EmployeeId) REFERENCES tbl_employee(emp_id)
                )
            ''')

        # Create tbl_task_status_master
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_task_status_master (
                status_id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                color_class TEXT,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create tbl_employee_status_master
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_employee_status_master (
                status_id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                color_class TEXT,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Seed default task statuses
        cursor.execute("SELECT COUNT(*) FROM tbl_task_status_master")
        if cursor.fetchone()[0] == 0:
            default_task_statuses = [
                ("Pending", "Task has been created but not started", "#f59e0b"),
                ("Work In Progress", "Task is currently being worked on", "#3b82f6"),
                ("Completed", "Task has been successfully completed", "#10b981"),
                ("Blocked", "Task is blocked by dependency or issue", "#ef4444"),
                ("On Hold", "Task is temporarily suspended", "#8b5cf6")
            ]
            cursor.executemany('''
                INSERT INTO tbl_task_status_master (name, description, color_class)
                VALUES (%s, %s, %s)
            ''', default_task_statuses)

        # Seed default employee statuses
        cursor.execute("SELECT COUNT(*) FROM tbl_employee_status_master")
        if cursor.fetchone()[0] == 0:
            default_employee_statuses = [
                ("active", "Employee is active and working", "#10b981"),
                ("inactive", "Employee has left or is inactive", "#ef4444"),
                ("On Leave", "Employee is currently on approved leave", "#f59e0b")
            ]
            cursor.executemany('''
                INSERT INTO tbl_employee_status_master (name, description, color_class)
                VALUES (%s, %s, %s)
            ''', default_employee_statuses)

        conn.commit()
        # Create tbl_task_status_master
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_task_status_master (
                status_id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                color_class TEXT,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create tbl_employee_status_master
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_employee_status_master (
                status_id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                color_class TEXT,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Seed default task statuses
        cursor.execute("SELECT COUNT(*) FROM tbl_task_status_master")
        if cursor.fetchone()[0] == 0:
            default_task_statuses = [
                ("Pending", "Task has been created but not started", "#f59e0b"),
                ("Work In Progress", "Task is currently being worked on", "#3b82f6"),
                ("Completed", "Task has been successfully completed", "#10b981"),
                ("Blocked", "Task is blocked by dependency or issue", "#ef4444"),
                ("On Hold", "Task is temporarily suspended", "#8b5cf6")
            ]
            cursor.executemany('''
                INSERT INTO tbl_task_status_master (name, description, color_class)
                VALUES (%s, %s, %s)
            ''', default_task_statuses)

        # Seed default employee statuses
        cursor.execute("SELECT COUNT(*) FROM tbl_employee_status_master")
        if cursor.fetchone()[0] == 0:
            default_employee_statuses = [
                ("active", "Employee is active and working", "#10b981"),
                ("inactive", "Employee has left or is inactive", "#ef4444"),
                ("On Leave", "Employee is currently on approved leave", "#f59e0b")
            ]
            cursor.executemany('''
                INSERT INTO tbl_employee_status_master (name, description, color_class)
                VALUES (%s, %s, %s)
            ''', default_employee_statuses)

        # Create tbl_daily_task
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_daily_task (
                daily_task_id SERIAL PRIMARY KEY,
                emp_id INTEGER NOT NULL,
                task_title TEXT NOT NULL,
                task_desc TEXT NOT NULL,
                project_status TEXT NOT NULL,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                admin_feedback TEXT,
                task_hours INTEGER DEFAULT 0,
                FOREIGN KEY (emp_id) REFERENCES tbl_employee (emp_id)
            )
        ''')

        cursor.execute('ALTER TABLE tbl_daily_task ADD COLUMN IF NOT EXISTS task_hours INTEGER DEFAULT 0')

        # Create tbl_registration_requests
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_registration_requests (
                request_id SERIAL PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                gender TEXT,
                dob DATE,
                address TEXT,
                phone_no TEXT,
                email TEXT,
                password TEXT,
                department TEXT,
                status TEXT DEFAULT 'pending',
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create TblAssets
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS TblAssets (
                AssetId SERIAL PRIMARY KEY,
                ItemName TEXT,
                Model TEXT,
                Price TEXT,
                Descriptions TEXT,
                Status TEXT DEFAULT 'Available',
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create TblAllocateAssets
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS TblAllocateAssets (
                AllocatedId SERIAL PRIMARY KEY,
                AssetId INTEGER REFERENCES TblAssets(AssetId),
                EmployeeId INTEGER REFERENCES tbl_employee(emp_id),
                AllocateDate DATE,
                Status TEXT DEFAULT 'Allocated',
                AllocatedBy TEXT,
                Description TEXT,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create TblAssetIssues
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS TblAssetIssues (
                IssueId SERIAL PRIMARY KEY,
                AssetId INTEGER REFERENCES TblAssets(AssetId),
                EmployeeId INTEGER REFERENCES tbl_employee(emp_id),
                IssueText TEXT,
                Status TEXT DEFAULT 'Open',
                ResolvedComment TEXT,
                ResolvedDate DATE,
                ReportedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create TblCareers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS TblCareers (
                CareerId SERIAL PRIMARY KEY,
                JobTitle TEXT,
                Exp TEXT,
                Sal TEXT,
                Location TEXT,
                Description TEXT,
                BannerImg TEXT,
                inserted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def hash_password(self, password):
        return password
