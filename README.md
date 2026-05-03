# Barangay Cawitan: A Web-Based Complaints Management System

This is a Django + MySQL web system for managing barangay resident complaints.

## Technology Stack

- Python
- Django
- MySQL
- HTML, CSS, JavaScript
- Bootstrap 5

## Version Compatibility

This project pins Django to `5.0.x` because many local XAMPP installations use MariaDB `10.4.x`. Newer Django versions require newer MariaDB versions:

- Django 5.0.x works with MariaDB 10.4.x.
- Django 5.1.x requires MariaDB 10.5 or later.
- Django 6.0.x requires MariaDB 10.6 or later.

If your database error says `MariaDB 10.6 or later is required`, reinstall the project dependencies after pulling the latest code:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Main Roles

- Resident: registers, logs in, submits complaints, uploads evidence, tracks complaint status, edits profile.
- Barangay Staff: logs in, views assigned complaints, updates status, adds remarks.
- Admin: monitors dashboard, manages residents/staff, assigns complaints, updates/deletes records, views reports.

## Project Setup Commands

Run these commands from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `mysqlclient` fails to install on Windows, install the matching Microsoft C++ Build Tools or use a Python version with available wheels.

## MySQL Database Setup

Open MySQL and run:

```sql
CREATE DATABASE barangay_cawitan_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'barangay_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON barangay_cawitan_db.* TO 'barangay_user'@'localhost';
FLUSH PRIVILEGES;
```

For local development with the root account, you can keep:

```env
DB_USER=root
DB_PASSWORD=
```

## Environment Variables

Edit `.env` in the project root:

```env
SECRET_KEY=change-this-secret-key
DEBUG=True
DB_NAME=barangay_cawitan_db
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306
```

## Django Project and App Creation Commands

This project has already been generated. If you were creating it manually from scratch, the equivalent commands would be:

```powershell
django-admin startproject barangay_cawitan_system .
python manage.py startapp accounts
python manage.py startapp complaints
python manage.py startapp dashboard
```

## Migration Commands

```powershell
python manage.py makemigrations
python manage.py migrate
```

## Create a Superuser

```powershell
python manage.py createsuperuser
```

After creating the superuser, log in to `/admin/` and set that user's `role` to `ADMIN` if needed. Superusers are also treated as barangay admins by the system.

## Run the Server

```powershell
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Useful URLs

- `/accounts/register/` - resident registration
- `/accounts/login/` - login
- `/` - role-based dashboard redirect
- `/complaints/` - complaint list
- `/complaints/submit/` - resident complaint submission
- `/admin-dashboard/` - admin dashboard
- `/accounts/staff/` - staff management
- `/complaints/reports/` - simple reports
- `/admin/` - Django admin panel

## File Structure

```text
barangay_cawitan_system/
├── manage.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
├── barangay_cawitan_system/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── templates/accounts/
│   └── static/accounts/
├── complaints/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── templates/complaints/
│   └── static/complaints/
├── dashboard/
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── templates/dashboard/
│   └── static/dashboard/
├── templates/
│   ├── base.html
│   ├── navbar.html
│   └── sidebar.html
├── static/
│   ├── css/main.css
│   ├── js/main.js
│   └── images/
└── media/
    └── complaint_uploads/
```

## How the System Works

1. Residents register through the public registration page. The system creates a `User` with the `RESIDENT` role and a linked `ResidentProfile`.
2. Residents submit complaints with category, title, description, incident location, incident date, and optional evidence file.
3. Admin users see all complaints, residents, staff accounts, and reports.
4. Admin users can create staff accounts and assign complaints to staff.
5. Staff users see only complaints assigned to them.
6. Staff and admins can update complaint status and add remarks.
7. When a complaint status changes, the resident receives a notification shown on the resident dashboard.

## Complaint Status Options

- Pending
- Under Review
- In Progress
- Resolved
- Rejected

## Suggested First Data to Add

In Django admin, add complaint categories such as:

- Noise Complaint
- Sanitation
- Road or Drainage
- Peace and Order
- Barangay Clearance Concern
- Other

## Notes for Beginners

- Backend logic lives in `models.py`, `forms.py`, and `views.py`.
- Page routes live in each app's `urls.py`.
- HTML templates are separated by app under `templates/`.
- CSS and JavaScript are in `static/`.
- Uploaded complaint evidence goes to `media/complaint_uploads/`.
- Role checks prevent residents from accessing staff/admin pages and prevent staff from accessing admin-only pages.
