-- Barangay Cawitan Complaint System - Sample Accounts
-- Paste this entire script into phpMyAdmin SQL tab and execute

USE barangay_cawitan_db;

-- ADMIN ACCOUNT
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role) 
VALUES ('admin', 'pbkdf2_sha256$1200000$AHj1vzPtav6pMgIAQWcyqJ$jFf6r1p+nh1wF9vuBCn1L/OwLErdAVl+sPsZqTq3zWg=', NULL, 1, 'System', 'Administrator', 'admin@barangay.gov', 1, 1, NOW(), 'ADMIN');

-- STAFF ACCOUNTS
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES ('staff_maria', 'pbkdf2_sha256$1200000$7O039zhz1Zn79hR9RW9Iwi$tXDkcjfmnALu1GBE2N+zDyxsZem8N2TyooKxKLi8A3o=', NULL, 0, 'Maria', 'Santos', 'maria.santos@barangay.gov', 1, 1, NOW(), 'STAFF');

INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES ('staff_juan', 'pbkdf2_sha256$1200000$7O039zhz1Zn79hR9RW9Iwi$tXDkcjfmnALu1GBE2N+zDyxsZem8N2TyooKxKLi8A3o=', NULL, 0, 'Juan', 'Dela Cruz', 'juan.dela.cruz@barangay.gov', 1, 1, NOW(), 'STAFF');

INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES ('staff_rosa', 'pbkdf2_sha256$1200000$7O039zhz1Zn79hR9RW9Iwi$tXDkcjfmnALu1GBE2N+zDyxsZem8N2TyooKxKLi8A3o=', NULL, 0, 'Rosa', 'Reyes', 'rosa.reyes@barangay.gov', 1, 1, NOW(), 'STAFF');

-- RESIDENT ACCOUNTS
INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES ('resident_ana', 'pbkdf2_sha256$1200000$6VKvgIR73rpnVfGWsDBZlQ$zKLTAPa5EGna9nx/rIHhPDJ8tsqcJWzVK0QbXansIeo=', NULL, 0, 'Ana', 'Villareal', 'ana.villareal@email.com', 0, 1, NOW(), 'RESIDENT');

INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES ('resident_pedro', 'pbkdf2_sha256$1200000$6VKvgIR73rpnVfGWsDBZlQ$zKLTAPa5EGna9nx/rIHhPDJ8tsqcJWzVK0QbXansIeo=', NULL, 0, 'Pedro', 'Garcia', 'pedro.garcia@email.com', 0, 1, NOW(), 'RESIDENT');

INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES ('resident_lucia', 'pbkdf2_sha256$1200000$6VKvgIR73rpnVfGWsDBZlQ$zKLTAPa5EGna9nx/rIHhPDJ8tsqcJWzVK0QbXansIeo=', NULL, 0, 'Lucia', 'Bautista', 'lucia.bautista@email.com', 0, 1, NOW(), 'RESIDENT');

INSERT IGNORE INTO accounts_user (username, password, last_login, is_superuser, first_name, last_name, email, is_staff, is_active, date_joined, role)
VALUES ('resident_carlos', 'pbkdf2_sha256$1200000$6VKvgIR73rpnVfGWsDBZlQ$zKLTAPa5EGna9nx/rIHhPDJ8tsqcJWzVK0QbXansIeo=', NULL, 0, 'Carlos', 'Moreno', 'carlos.moreno@email.com', 0, 1, NOW(), 'RESIDENT');

-- STAFF PROFILES
INSERT IGNORE INTO accounts_staffprofile (user_id, position, phone_number, responsibilities, created_at)
SELECT id, 'Complaints Coordinator', '+63 917-123-4567', 'Receive and review complaints\nCategorize complaints by type and urgency\nAssign or forward complaints to the correct handler\nUpdate complaint status and internal notes\nCommunicate updates to complainants\nUpload evidence, inspection notes, or resolution proof\nMonitor overdue and urgent complaints\nPrepare complaint summaries and reports', NOW()
FROM accounts_user WHERE username = 'staff_maria' LIMIT 1;

INSERT IGNORE INTO accounts_staffprofile (user_id, position, phone_number, responsibilities, created_at)
SELECT id, 'Barangay Councilor', '+63 917-567-8901', 'Receive and review complaints\nCategorize complaints by type and urgency\nAssign or forward complaints to the correct handler\nUpdate complaint status and internal notes\nCommunicate updates to complainants\nUpload evidence, inspection notes, or resolution proof\nMonitor overdue and urgent complaints\nPrepare complaint summaries and reports', NOW()
FROM accounts_user WHERE username = 'staff_juan' LIMIT 1;

INSERT IGNORE INTO accounts_staffprofile (user_id, position, phone_number, responsibilities, created_at)
SELECT id, 'Administrative Officer', '+63 917-987-6543', 'Receive and review complaints\nCategorize complaints by type and urgency\nAssign or forward complaints to the correct handler\nUpdate complaint status and internal notes\nCommunicate updates to complainants\nUpload evidence, inspection notes, or resolution proof\nMonitor overdue and urgent complaints\nPrepare complaint summaries and reports', NOW()
FROM accounts_user WHERE username = 'staff_rosa' LIMIT 1;

-- RESIDENT PROFILES
INSERT IGNORE INTO accounts_residentprofile (user_id, phone_number, address, birth_date, created_at)
SELECT id, '09171234567', '123 Main Street, Cawitan', '1985-01-15', NOW()
FROM accounts_user WHERE username = 'resident_ana' LIMIT 1;

INSERT IGNORE INTO accounts_residentprofile (user_id, phone_number, address, birth_date, created_at)
SELECT id, '09175678901', '456 Oak Avenue, Cawitan', '1985-01-15', NOW()
FROM accounts_user WHERE username = 'resident_pedro' LIMIT 1;

INSERT IGNORE INTO accounts_residentprofile (user_id, phone_number, address, birth_date, created_at)
SELECT id, '09179876543', '789 Maple Drive, Cawitan', '1985-01-15', NOW()
FROM accounts_user WHERE username = 'resident_lucia' LIMIT 1;

INSERT IGNORE INTO accounts_residentprofile (user_id, phone_number, address, birth_date, created_at)
SELECT id, '09175554321', '321 Pine Street, Cawitan', '1985-01-15', NOW()
FROM accounts_user WHERE username = 'resident_carlos' LIMIT 1;
