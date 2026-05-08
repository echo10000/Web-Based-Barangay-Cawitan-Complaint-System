# Deploying to PythonAnywhere

This project is a Django + MySQL app. Use PythonAnywhere's manual web app setup.

## 1. Upload the project

Recommended: push this project to GitHub, then clone it from a PythonAnywhere Bash console:

```bash
cd ~
git clone https://github.com/YOUR_GITHUB_USERNAME/cawitancomplaint.git
cd cawitancomplaint
```

If you upload files manually, make sure the folder that contains `manage.py` is under `/home/YOUR_PYTHONANYWHERE_USERNAME/`.

## 2. Create the virtualenv

Use a Python version supported by your PythonAnywhere account:

```bash
mkvirtualenv --python=/usr/bin/python3.11 cawitancomplaint-venv
pip install --upgrade pip
pip install -r requirements.txt
```

If `mysqlclient` fails, try:

```bash
pip install mysqlclient
pip install -r requirements.txt
```

## 3. Create the MySQL database

In PythonAnywhere, open the **Databases** tab.

1. Set your MySQL password.
2. Create a database named `barangay_cawitan_db`.
3. PythonAnywhere will expose its full name as:

```text
YOUR_PYTHONANYWHERE_USERNAME$barangay_cawitan_db
```

## 4. Add production environment variables

Copy `.env.pythonanywhere.example` to `.env` on PythonAnywhere:

```bash
cp .env.pythonanywhere.example .env
nano .env
```

Replace every `yourusername` placeholder with your PythonAnywhere username. Generate a real `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Your PythonAnywhere database values should look like:

```env
DB_NAME=yourusername$barangay_cawitan_db
DB_USER=yourusername
DB_PASSWORD=your-pythonanywhere-mysql-password
DB_HOST=yourusername.mysql.pythonanywhere-services.com
DB_PORT=3306
```

## 5. Run migrations and collect static files

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

After creating the superuser, log in to `/admin/` and set the user's role to `ADMIN` if needed.

## 6. Create the web app

In PythonAnywhere's **Web** tab:

1. Add a new web app.
2. Choose **Manual configuration**.
3. Choose the same Python version as the virtualenv.
4. Set **Virtualenv** to:

```text
/home/YOUR_PYTHONANYWHERE_USERNAME/.virtualenvs/cawitancomplaint-venv
```

5. Set **Source code** and **Working directory** to:

```text
/home/YOUR_PYTHONANYWHERE_USERNAME/cawitancomplaint
```

## 7. Configure the WSGI file

Open the WSGI file from the Web tab, delete the starter code, and use:

```python
import os
import sys

path = "/home/YOUR_PYTHONANYWHERE_USERNAME/cawitancomplaint"
if path not in sys.path:
    sys.path.insert(0, path)

os.chdir(path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "barangay_cawitan_system.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Replace `YOUR_PYTHONANYWHERE_USERNAME`.

## 8. Configure static and media files

In the Web tab's **Static files** section, add:

```text
URL:       /static/
Directory: /home/YOUR_PYTHONANYWHERE_USERNAME/cawitancomplaint/staticfiles
```

For uploaded complaint evidence, also add:

```text
URL:       /media/
Directory: /home/YOUR_PYTHONANYWHERE_USERNAME/cawitancomplaint/media
```

Click **Reload** on the Web tab after saving mappings.

## 9. Verify

Open:

```text
https://YOUR_PYTHONANYWHERE_USERNAME.pythonanywhere.com/
```

If the page errors, check the Web tab's error log first. The most common issues are incorrect `.env` database values, a missing virtualenv path, or a typo in the WSGI project path.
