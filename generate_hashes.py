import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barangay_cawitan_system.settings')
django.setup()

from django.contrib.auth.hashers import make_password

passwords = {
    'Admin123!': make_password('Admin123!'),
    'Staff123!': make_password('Staff123!'),
    'Resident123!': make_password('Resident123!'),
}

for pwd, hashed in passwords.items():
    print(f"Password: {pwd}")
    print(f"Hash: {hashed}\n")
