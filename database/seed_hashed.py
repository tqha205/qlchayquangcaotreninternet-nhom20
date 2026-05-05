"""
seed_hashed.py
==============
Chay file nay de seed cac tai khoan mau voi mat khau duoc ma hoa bang Werkzeug.
Neu tai khoan da ton tai, se cap nhat lai mat khau (hash moi).

Cach dung:
    cd d:\\software_chay_quang_cao_online
    python database/seed_hashed.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash
import mysql.connector
from config import MYSQL_CONFIG

# --- Danh sach tai khoan mau ---
SAMPLE_USERS = [
    {'username': 'admin',    'password': 'Admin@123',  'role': 'admin',    'customer_id': None},
    {'username': 'marketer', 'password': 'Mark@123',   'role': 'marketer', 'customer_id': None},
    {'username': 'client',   'password': 'Client@123', 'role': 'client',   'customer_id': 1},
]


def seed():
    print("[DB] Ket noi den database:", MYSQL_CONFIG.get('database'))
    try:
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        inserted = 0
        updated  = 0

        for u in SAMPLE_USERS:
            hashed_pw = generate_password_hash(u['password'])

            # Kiem tra user da ton tai chua
            cursor.execute("SELECT id FROM users WHERE username = %s", (u['username'],))
            existing = cursor.fetchone()

            if existing:
                # Update lai mat khau (hash moi) cho tai khoan cu (plaintext cu khong con dung duoc)
                cursor.execute(
                    "UPDATE users SET password = %s, is_active = 1 WHERE username = %s",
                    (hashed_pw, u['username'])
                )
                print(f"  [UPDATE] {u['username']} / {u['password']}  -> Da cap nhat mat khau hash moi")
                updated += 1
            else:
                cursor.execute(
                    "INSERT INTO users (username, password, role, customer_id, is_active) VALUES (%s, %s, %s, %s, 1)",
                    (u['username'], hashed_pw, u['role'], u['customer_id'])
                )
                print(f"  [CREATE] {u['username']} / {u['password']}  -> Da tao moi (role: {u['role']})")
                inserted += 1

        conn.commit()
        cursor.close()
        conn.close()

        print()
        print(f"[DONE] Hoan tat! {inserted} tai khoan moi, {updated} tai khoan da cap nhat.")
        print()
        print("[INFO] Thong tin dang nhap:")
        print("  +------------+-------------+-----------+")
        print("  | Username   | Password    | Role      |")
        print("  +------------+-------------+-----------+")
        for u in SAMPLE_USERS:
            print(f"  | {u['username']:<10} | {u['password']:<11} | {u['role']:<9} |")
        print("  +------------+-------------+-----------+")

    except mysql.connector.Error as err:
        print(f"[ERROR] Loi ket noi DB: {err}")
        print("Hay kiem tra lai thong tin trong config.py (host, user, password, database).")
        sys.exit(1)


if __name__ == '__main__':
    seed()
