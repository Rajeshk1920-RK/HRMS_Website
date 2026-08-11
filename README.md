# Project Tracking System (HRMS)

A web-based Human Resource Management System (HRMS) and Project Tracking application built with Flask and PostgreSQL.

## Features

- **Employee Management**: Create, edit, and delete employee records; manage registration requests.
- **Task & Activity Tracking**: Log daily working hours, assign tasks, update progress, and view daily task feeds.
- **Leave Management**: Request leave, manage leave types, and review holiday schedules.
- **Expense Claims**: Submit claims with invoice receipts and track reimbursement statuses.
- **Assets Allocation**: Manage corporate inventory, allocate assets, and track issues.
- **Wiki & Knowledge Base**: Categories and articles for internal company guides.
- **Unified Profiles**: View and edit user profiles, upload avatars, and view real-time working hour statistics (Today, Week, Month).

---

## Prerequisites

Ensure you have the following installed on your local machine:
- **Python 3.8+**
- **PostgreSQL** (running and accessible)

---

## Installation & Setup

Follow these steps to set up and run the application locally:

### 1. Set Up Virtual Environment
Create and activate a Python virtual environment inside the repository:
```bash
# Create venv
python3 -m venv venv

# Activate venv (macOS/Linux)
source venv/bin/activate

# Activate venv (Windows)
venv\Scripts\activate
```

### 2. Install Dependencies
Install all required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Database Setup & Environment Variables
Create a `.env` file in the root of the project with the following configuration:
```env
# Flask configuration
FLASK_APP=run.py
FLASK_DEBUG=True
SECRET_KEY=your_secret_key_here

# PostgreSQL configuration
PG_HOST=localhost
PG_PORT=5432
PG_DBNAME=project_tracking
PG_USER=your_postgres_username
PG_PASSWORD=your_postgres_password
```
Make sure you have created the target database (e.g. `project_tracking`) in your PostgreSQL instance. The application automatically initializes all schemas, database tables, and default seed data on startup.

---

## Running the Application

To start the Flask development server:
```bash
python run.py
```
The server will start running on **`http://localhost:50001`**.

### Default Admin Login
On the first run, the database is seeded with a default Admin account:
- **Login ID / Email**: `admin@company.com`
- **Password**: `admin123`
