#!/usr/bin/env python
"""
Load sample data into the database using Python instead of MySQL CLI
This bypasses the need for mysql command-line tool to be in PATH
"""

import os
import sys
import django
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barangay_cawitan_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

# Patch the version check before Django setup to support MariaDB 10.4
from django.db.backends.mysql.base import DatabaseWrapper
original_check = DatabaseWrapper.check_database_version_supported
DatabaseWrapper.check_database_version_supported = lambda self: None

django.setup()

from django.db import connection
from pathlib import Path

def load_sql_file():
    """Load and execute the SQL file"""
    
    sql_file = Path(__file__).parent / 'create_sample_data.sql'
    
    if not sql_file.exists():
        print(f"❌ Error: {sql_file} not found!")
        return False
    
    try:
        # Read the SQL file
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Split into individual statements (handle comments and multiple statements)
        statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            # Skip comments and empty lines
            if line.strip().startswith('--') or not line.strip():
                continue
            
            current_statement += line + "\n"
            
            # When we hit a semicolon, execute the statement
            if line.strip().endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        # Execute each statement
        print("\n" + "="*70)
        print("LOADING SAMPLE DATA INTO DATABASE")
        print("="*70 + "\n")
        
        with connection.cursor() as cursor:
            for i, statement in enumerate(statements, 1):
                if statement:
                    try:
                        cursor.execute(statement)
                        print(f"✓ Statement {i} executed successfully")
                    except Exception as e:
                        print(f"⚠ Statement {i} skipped: {e}")
        
        print("\n" + "="*70)
        print("✅ SAMPLE DATA LOADED SUCCESSFULLY!")
        print("="*70)
        print("\nYou can now login with these accounts:")
        print("  • Admin: admin / Admin123!")
        print("  • Staff: staff_maria / Staff123!")
        print("  • Resident: resident_ana / Resident123!")
        print("\nStart the server with: python manage.py runserver\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading SQL file: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = load_sql_file()
    sys.exit(0 if success else 1)
