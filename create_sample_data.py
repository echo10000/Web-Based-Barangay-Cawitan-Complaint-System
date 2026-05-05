#!/usr/bin/env python
"""
Script to create sample accounts for Barangay Cawitan Complaint System
Creates accounts directly using SQL to bypass version check issues
"""

import os
import sys
import django
from datetime import date
import pymysql
from django.contrib.auth.hashers import make_password

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barangay_cawitan_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

# Load settings
from django.conf import settings
from decouple import config

# Database configuration from .env
DB_NAME = config("DB_NAME", default="barangay_cawitan_db")
DB_USER = config("DB_USER", default="root")
DB_PASSWORD = config("DB_PASSWORD", default="")
DB_HOST = config("DB_HOST", default="localhost")
DB_PORT = int(config("DB_PORT", default="3306"))

from django.contrib.auth import get_user_model
from accounts.models import ResidentProfile, StaffProfile

User = get_user_model()


def create_sample_accounts():
    """Create sample accounts for all user roles"""
    
    print("\n" + "="*60)
    print("Creating Sample Accounts for Barangay Cawitan System")
    print("="*60 + "\n")
    
    # Admin Account
    print("[1/3] Creating Admin account...")
    admin, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@barangay.gov",
            "first_name": "System",
            "last_name": "Administrator",
            "role": User.Role.ADMIN,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if created:
        admin.set_password("Admin123!")
        admin.save()
        print("✓ Created Admin account")
        print("  └─ Username: admin | Password: Admin123!\n")
    else:
        print("✓ Admin account already exists\n")

    # Staff Accounts
    print("[2/3] Creating Staff accounts...")
    staff_accounts = [
        {
            "username": "staff_maria",
            "email": "maria.santos@barangay.gov",
            "first_name": "Maria",
            "last_name": "Santos",
            "position": "Complaints Coordinator",
            "password": "Staff123!",
        },
        {
            "username": "staff_juan",
            "email": "juan.dela.cruz@barangay.gov",
            "first_name": "Juan",
            "last_name": "Dela Cruz",
            "position": "Barangay Councilor",
            "password": "Staff123!",
        },
        {
            "username": "staff_rosa",
            "email": "rosa.reyes@barangay.gov",
            "first_name": "Rosa",
            "last_name": "Reyes",
            "position": "Administrative Officer",
            "password": "Staff123!",
        },
    ]

    for i, staff_data in enumerate(staff_accounts, 1):
        password = staff_data.pop("password")
        position = staff_data.pop("position")
        staff_user, created = User.objects.get_or_create(
            username=staff_data["username"],
            defaults={
                **staff_data,
                "role": User.Role.STAFF,
                "is_staff": True,
            },
        )
        if created:
            staff_user.set_password(password)
            staff_user.save()
            StaffProfile.objects.get_or_create(
                user=staff_user,
                defaults={
                    "position": position,
                    "phone_number": "+63 9XX-XXX-XXXX",
                },
            )
            print(f"✓ Created Staff account ({i}/3)")
            print(f"  └─ Username: {staff_data['username']} | Password: {password}")
        else:
            print(f"✓ Staff account {staff_data['username']} already exists")
    
    print()

    # Resident Accounts
    print("[3/3] Creating Resident accounts...")
    resident_accounts = [
        {
            "username": "resident_ana",
            "email": "ana.villareal@email.com",
            "first_name": "Ana",
            "last_name": "Villareal",
            "address": "123 Main Street, Cawitan",
            "phone_number": "09171234567",
            "password": "Resident123!",
        },
        {
            "username": "resident_pedro",
            "email": "pedro.garcia@email.com",
            "first_name": "Pedro",
            "last_name": "Garcia",
            "address": "456 Oak Avenue, Cawitan",
            "phone_number": "09175678901",
            "password": "Resident123!",
        },
        {
            "username": "resident_lucia",
            "email": "lucia.bautista@email.com",
            "first_name": "Lucia",
            "last_name": "Bautista",
            "address": "789 Maple Drive, Cawitan",
            "phone_number": "09179876543",
            "password": "Resident123!",
        },
        {
            "username": "resident_carlos",
            "email": "carlos.moreno@email.com",
            "first_name": "Carlos",
            "last_name": "Moreno",
            "address": "321 Pine Street, Cawitan",
            "phone_number": "09175554321",
            "password": "Resident123!",
        },
    ]

    for i, resident_data in enumerate(resident_accounts, 1):
        password = resident_data.pop("password")
        phone_number = resident_data.pop("phone_number")
        address = resident_data.pop("address")
        resident_user, created = User.objects.get_or_create(
            username=resident_data["username"],
            defaults={
                **resident_data,
                "role": User.Role.RESIDENT,
            },
        )
        if created:
            resident_user.set_password(password)
            resident_user.save()
            ResidentProfile.objects.get_or_create(
                user=resident_user,
                defaults={
                    "phone_number": phone_number,
                    "address": address,
                    "birth_date": date(1985, 1, 15),
                },
            )
            print(f"✓ Created Resident account ({i}/4)")
            print(f"  └─ Username: {resident_data['username']} | Password: {password}")
        else:
            print(f"✓ Resident account {resident_data['username']} already exists")
    
    print("\n" + "="*60)
    print("✓ Sample accounts creation completed!")
    print("="*60 + "\n")
    
    # Summary
    print("ACCOUNT SUMMARY:")
    print("-" * 60)
    print("\n1. ADMIN ACCOUNT:")
    print("   Username: admin")
    print("   Password: Admin123!")
    print("\n2. STAFF ACCOUNTS:")
    for staff in staff_accounts:
        print(f"   Username: {staff['username']}")
        print(f"   Position: {staff['position']}")
        print(f"   Password: Staff123!")
        print()
    
    print("3. RESIDENT ACCOUNTS:")
    for resident in resident_accounts:
        print(f"   Username: {resident['username']}")
        print(f"   Email: {resident['email']}")
        print(f"   Password: Resident123!")
        print()
    
    print("-" * 60)
    print("\nYou can now login with any of these accounts!")
    print()


if __name__ == "__main__":
    try:
        create_sample_accounts()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
