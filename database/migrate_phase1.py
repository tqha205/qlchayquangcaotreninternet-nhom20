"""
migrate_phase1.py
=================
Script migration cho Phase 1: Them cac cot moi vao database hien co.
Chay mot lan: python database/migrate_phase1.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from config import MYSQL_CONFIG

MIGRATIONS = [
    ("users",     "ALTER TABLE users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1"),
    ("users",     "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("campaigns", "ALTER TABLE campaigns ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("inquiries", "ALTER TABLE inquiries ADD COLUMN status VARCHAR(20) DEFAULT 'new'"),
]


def migrate():
    print("[DB] Ket noi den database:", MYSQL_CONFIG.get('database'))
    try:
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        for table, sql in MIGRATIONS:
            try:
                cursor.execute(sql)
                col = sql.split("ADD COLUMN")[1].strip().split()[0]
                print(f"  [OK]   {table}.{col} -> Da them thanh cong")
            except mysql.connector.Error as e:
                if e.errno == 1060:  # Duplicate column
                    col = sql.split("ADD COLUMN")[1].strip().split()[0]
                    print(f"  [SKIP] {table}.{col} -> Da ton tai, bo qua")
                else:
                    print(f"  [ERR]  {sql[:60]}... -> {e}")

        conn.commit()
        cursor.close()
        conn.close()
        print()
        print("[DONE] Migration Phase 1 hoan tat!")

    except mysql.connector.Error as err:
        print(f"[ERROR] Loi ket noi DB: {err}")
        sys.exit(1)


if __name__ == '__main__':
    migrate()
