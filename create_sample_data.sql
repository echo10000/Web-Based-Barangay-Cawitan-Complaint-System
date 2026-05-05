-- ============================================================================
-- Sample Accounts for Barangay Cawitan Complaint System
-- ============================================================================
-- This SQL file creates sample accounts for testing purposes
-- Run this in your MariaDB/MySQL database: barangay_cawitan_db
--
-- ACCOUNTS CREATED:
-- 1 Admin, 3 Staff, 4 Residents
-- ============================================================================

USE barangay_cawitan_db;

-- ADMIN ACCOUNT
-- Username: admin | Password: Admin123!
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role) 
VALUES (
    'admin',
    'pbkdf2_sha256$1200000$AHj1vzPtav6pMgIAQWcyqJ$jFf6r1p+nh1wF9vuBCn1L/OwLErdAVl+sPsZqTq3zWg=',
    NULL,
    1,
    'System',
    'Administrator',
    'admin@barangay.gov',
    1,
    1,
    NOW(),
    'ADMIN'
);

-- STAFF ACCOUNTS
-- Staff 1: Maria Santos (Complaints Coordinator)
-- Username: staff_maria | Password: Staff123!
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES (
    'staff_maria',
    'pbkdf2_sha256$1200000$7O039zhz1Zn79hR9RW9Iwi$tXDkcjfmnALu1GBE2N+zDyxsZem8N2TyooKxKLi8A3o=',
    NULL,
    0,
    'Maria',
    'Santos',
    'maria.santos@barangay.gov',
    1,
    1,
    NOW(),
    'STAFF'
);

-- Staff 2: Juan Dela Cruz (Barangay Councilor)
-- Username: staff_juan | Password: Staff123!
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES (
    'staff_juan',
    'pbkdf2_sha256$1200000$7O039zhz1Zn79hR9RW9Iwi$tXDkcjfmnALu1GBE2N+zDyxsZem8N2TyooKxKLi8A3o=',
    NULL,
    0,
    'Juan',
    'Dela Cruz',
    'juan.dela.cruz@barangay.gov',
    1,
    1,
    NOW(),
    'STAFF'
);

-- Staff 3: Rosa Reyes (Administrative Officer)
-- Username: staff_rosa | Password: Staff123!
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES (
    'staff_rosa',
    'pbkdf2_sha256$1200000$7O039zhz1Zn79hR9RW9Iwi$tXDkcjfmnALu1GBE2N+zDyxsZem8N2TyooKxKLi8A3o=',
    NULL,
    0,
    'Rosa',
    'Reyes',
    'rosa.reyes@barangay.gov',
    1,
    1,
    NOW(),
    'STAFF'
);

-- RESIDENT ACCOUNTS
-- Resident 1: Ana Villareal
-- Username: resident_ana | Password: Resident123!
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES (
    'resident_ana',
    'pbkdf2_sha256$1200000$6VKvgIR73rpnVfGWsDBZlQ$zKLTAPa5EGna9nx/rIHhPDJ8tsqcJWzVK0QbXansIeo=',
    NULL,
    0,
    'Ana',
    'Villareal',
    'ana.villareal@email.com',
    0,
    1,
    NOW(),
    'RESIDENT'
);

-- Resident 2: Pedro Garcia
-- Username: resident_pedro | Password: Resident123!
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES (
    'resident_pedro',
    'pbkdf2_sha256$1200000$6VKvgIR73rpnVfGWsDBZlQ$zKLTAPa5EGna9nx/rIHhPDJ8tsqcJWzVK0QbXansIeo=',
    NULL,
    0,
    'Pedro',
    'Garcia',
    'pedro.garcia@email.com',
    0,
    1,
    NOW(),
    'RESIDENT'
);

-- Resident 3: Lucia Bautista
-- Username: resident_lucia | Password: Resident123!
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES (
    'resident_lucia',
    'pbkdf2_sha256$1200000$6VKvgIR73rpnVfGWsDBZlQ$zKLTAPa5EGna9nx/rIHhPDJ8tsqcJWzVK0QbXansIeo=',
    NULL,
    0,
    'Lucia',
    'Bautista',
    'lucia.bautista@email.com',
    0,
    1,
    NOW(),
    'RESIDENT'
);

-- Resident 4: Carlos Moreno
-- Username: resident_carlos | Password: Resident123!
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES (
    'resident_carlos',
    'pbkdf2_sha256$1200000$6VKvgIR73rpnVfGWsDBZlQ$zKLTAPa5EGna9nx/rIHhPDJ8tsqcJWzVK0QbXansIeo=',
    NULL,
    0,
    'Carlos',
    'Moreno',
    'carlos.moreno@email.com',
    0,
    1,
    NOW(),
    'RESIDENT'
);

-- ============================================================================
-- CREATE STAFF PROFILES
-- ============================================================================

-- Staff Profile 1: Maria Santos
INSERT IGNORE INTO accounts_staffprofile (user_id, position, phone_number, responsibilities, created_at)
SELECT id, 'Complaints Coordinator', '+63 917-123-4567',
'Receive and review complaints
Categorize complaints by type and urgency
Assign or forward complaints to the correct handler
Update complaint status and internal notes
Communicate updates to complainants
Upload evidence, inspection notes, or resolution proof
Monitor overdue and urgent complaints
Prepare complaint summaries and reports',
NOW()
FROM accounts_user WHERE username = 'staff_maria' LIMIT 1;

-- Staff Profile 2: Juan Dela Cruz
INSERT IGNORE INTO accounts_staffprofile (user_id, position, phone_number, responsibilities, created_at)
SELECT id, 'Barangay Councilor', '+63 917-567-8901',
'Receive and review complaints
Categorize complaints by type and urgency
Assign or forward complaints to the correct handler
Update complaint status and internal notes
Communicate updates to complainants
Upload evidence, inspection notes, or resolution proof
Monitor overdue and urgent complaints
Prepare complaint summaries and reports',
NOW()
FROM accounts_user WHERE username = 'staff_juan' LIMIT 1;

-- Staff Profile 3: Rosa Reyes
INSERT IGNORE INTO accounts_staffprofile (user_id, position, phone_number, responsibilities, created_at)
SELECT id, 'Administrative Officer', '+63 917-987-6543',
'Receive and review complaints
Categorize complaints by type and urgency
Assign or forward complaints to the correct handler
Update complaint status and internal notes
Communicate updates to complainants
Upload evidence, inspection notes, or resolution proof
Monitor overdue and urgent complaints
Prepare complaint summaries and reports',
NOW()
FROM accounts_user WHERE username = 'staff_rosa' LIMIT 1;

-- ============================================================================
-- CREATE RESIDENT PROFILES
-- ============================================================================

-- Resident Profile 1: Ana Villareal
INSERT IGNORE INTO accounts_residentprofile (user_id, phone_number, address, birth_date, created_at)
SELECT id, '09171234567', '123 Main Street, Cawitan', '1985-01-15', NOW()
FROM accounts_user WHERE username = 'resident_ana' LIMIT 1;

-- Resident Profile 2: Pedro Garcia
INSERT IGNORE INTO accounts_residentprofile (user_id, phone_number, address, birth_date, created_at)
SELECT id, '09175678901', '456 Oak Avenue, Cawitan', '1985-01-15', NOW()
FROM accounts_user WHERE username = 'resident_pedro' LIMIT 1;

-- Resident Profile 3: Lucia Bautista
INSERT IGNORE INTO accounts_residentprofile (user_id, phone_number, address, birth_date, created_at)
SELECT id, '09179876543', '789 Maple Drive, Cawitan', '1985-01-15', NOW()
FROM accounts_user WHERE username = 'resident_lucia' LIMIT 1;

-- Resident Profile 4: Carlos Moreno
INSERT IGNORE INTO accounts_residentprofile (user_id, phone_number, address, birth_date, created_at)
SELECT id, '09175554321', '321 Pine Street, Cawitan', '1985-01-15', NOW()
FROM accounts_user WHERE username = 'resident_carlos' LIMIT 1;

-- ============================================================================
-- SAMPLE DATA INSERTION COMPLETE
-- ============================================================================
-- All accounts have been created successfully!
-- You can now login with any of the credentials above.
-- ============================================================================
