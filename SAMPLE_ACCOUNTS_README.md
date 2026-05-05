# Sample Accounts for Barangay Cawitan Complaint System

This file contains sample accounts for testing the Barangay Cawitan Complaint System. The accounts have been created with all necessary profiles and roles.

## How to Create the Sample Accounts

### Option 1: Using the SQL File (Recommended)

1. **Make sure your database exists and is migrated**:
   ```bash
   python manage.py migrate
   ```

2. **Run the SQL file**:
   ```bash
   # On Windows (using command line or MySQL client):
   mysql -u root -p barangay_cawitan_db < create_sample_data.sql
   
   # Or in MySQL/MariaDB client:
   source create_sample_data.sql;
   ```

3. **Verify the accounts were created**:
   ```bash
   python manage.py shell
   >>> from accounts.models import User
   >>> User.objects.count()  # Should show 8 users (1 admin + 3 staff + 4 residents)
   >>> User.objects.values_list('username', 'role')
   ```

## Sample Accounts Created

### 1️⃣ ADMIN Account (1)
```
Username: admin
Password: Admin123!
Role: Administrator
Email: admin@barangay.gov
```

### 2️⃣ STAFF Accounts (3)

#### Staff 1: Maria Santos
```
Username: staff_maria
Password: Staff123!
Position: Complaints Coordinator
Email: maria.santos@barangay.gov
Phone: +63 917-123-4567
```

#### Staff 2: Juan Dela Cruz
```
Username: staff_juan
Password: Staff123!
Position: Barangay Councilor
Email: juan.dela.cruz@barangay.gov
Phone: +63 917-567-8901
```

#### Staff 3: Rosa Reyes
```
Username: staff_rosa
Password: Staff123!
Position: Administrative Officer
Email: rosa.reyes@barangay.gov
Phone: +63 917-987-6543
```

### 3️⃣ RESIDENT Accounts (4)

#### Resident 1: Ana Villareal
```
Username: resident_ana
Password: Resident123!
Email: ana.villareal@email.com
Phone: 09171234567
Address: 123 Main Street, Cawitan
Birth Date: January 15, 1985
```

#### Resident 2: Pedro Garcia
```
Username: resident_pedro
Password: Resident123!
Email: pedro.garcia@email.com
Phone: 09175678901
Address: 456 Oak Avenue, Cawitan
Birth Date: January 15, 1985
```

#### Resident 3: Lucia Bautista
```
Username: resident_lucia
Password: Resident123!
Email: lucia.bautista@email.com
Phone: 09179876543
Address: 789 Maple Drive, Cawitan
Birth Date: January 15, 1985
```

#### Resident 4: Carlos Moreno
```
Username: resident_carlos
Password: Resident123!
Email: carlos.moreno@email.com
Phone: 09175554321
Address: 321 Pine Street, Cawitan
Birth Date: January 15, 1985
```

## Features of These Sample Accounts

✅ **All accounts are fully configured** with:
- User profiles (StaffProfile for staff, ResidentProfile for residents)
- Appropriate roles and permissions
- Contact information and addresses
- Staff members have pre-assigned responsibilities

✅ **Testing capabilities**:
- Test admin dashboard functionality
- Test staff complaint handling workflows
- Test resident complaint submission and tracking
- Test role-based access control

## Default Passwords

All accounts use strong passwords for testing:
- **Admin**: `Admin123!`
- **Staff**: `Staff123!`
- **Residents**: `Resident123!`

⚠️ **Important**: Change all passwords before deploying to production!

## Troubleshooting

### If you get "Access denied for user 'root'" error:
```bash
# Provide password if needed:
mysql -u root -p barangay_cawitan_db < create_sample_data.sql
# Enter your database password when prompted
```

### If table doesn't exist error:
Make sure you've run migrations first:
```bash
python manage.py migrate
```

### If accounts already exist:
The SQL file uses `INSERT IGNORE` which won't duplicate existing accounts. To reset and recreate:

1. **Delete the sample accounts** (WARNING: This deletes user data):
   ```sql
   DELETE FROM accounts_residentprofile WHERE user_id IN (SELECT id FROM accounts_user WHERE username IN ('resident_ana', 'resident_pedro', 'resident_lucia', 'resident_carlos'));
   DELETE FROM accounts_staffprofile WHERE user_id IN (SELECT id FROM accounts_user WHERE username IN ('staff_maria', 'staff_juan', 'staff_rosa'));
   DELETE FROM accounts_user WHERE username IN ('admin', 'staff_maria', 'staff_juan', 'staff_rosa', 'resident_ana', 'resident_pedro', 'resident_lucia', 'resident_carlos');
   ```

2. Then run the SQL file again:
   ```bash
   mysql -u root -p barangay_cawitan_db < create_sample_data.sql
   ```

## Next Steps

After creating the sample accounts:

1. Start the development server:
   ```bash
   python manage.py runserver
   ```

2. Open http://localhost:8000 in your browser

3. Login with any of the sample accounts to test the system

4. Try submitting a complaint as a resident
5. Review and respond to complaints as a staff member
6. View reports and analytics as an admin

Enjoy testing! 🎉
