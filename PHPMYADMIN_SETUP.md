# phpMyAdmin Quick Setup

## Steps to Load Sample Accounts in phpMyAdmin:

1. **Open phpMyAdmin** in your browser (usually http://localhost/phpmyadmin)

2. **Select your database** `barangay_cawitan_db` from the left sidebar

3. **Click the "SQL" tab** at the top

4. **Copy and paste the entire script** from `phpmyadmin_sample_accounts.sql` into the SQL query box

5. **Click "Go"** or press Ctrl+Enter to execute

6. **Done!** You should see success messages for all queries

---

## 📋 Quick Reference - Login Credentials

### ADMIN
```
Username: admin
Password: Admin123!
```

### STAFF
```
Username: staff_maria  |  Password: Staff123!
Username: staff_juan   |  Password: Staff123!
Username: staff_rosa   |  Password: Staff123!
```

### RESIDENTS
```
Username: resident_ana    |  Password: Resident123!
Username: resident_pedro  |  Password: Resident123!
Username: resident_lucia  |  Password: Resident123!
Username: resident_carlos |  Password: Resident123!
```

---

## ✅ Verify It Worked

Run this SQL query in phpMyAdmin to check:

```sql
SELECT username, role, email FROM accounts_user ORDER BY username;
```

You should see all 8 accounts listed!
