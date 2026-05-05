import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from config import MYSQL_CONFIG

def migrate():
    print("--- MIGRATION: ADDING TARGET_LINK TO CAMPAIGNS ---")
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # Thêm cột target_link vào bảng campaigns
        print("Checking for 'target_link' column in 'campaigns'...")
        cursor.execute("SHOW COLUMNS FROM campaigns LIKE 'target_link'")
        result = cursor.fetchone()

        if not result:
            print("Adding 'target_link' column...")
            cursor.execute("ALTER TABLE campaigns ADD COLUMN target_link TEXT AFTER platform")
            conn.commit()
            print("Migration successful (campaigns)!")
        else:
            print("'target_link' column already exists.")

        # Cập nhật bảng customers: thêm company và status
        print("Checking for 'company' column in 'customers'...")
        cursor.execute("SHOW COLUMNS FROM customers LIKE 'company'")
        if not cursor.fetchone():
            print("Adding 'company' column...")
            cursor.execute("ALTER TABLE customers ADD COLUMN company VARCHAR(255) AFTER phone")
            conn.commit()

        print("Checking for 'status' column in 'customers'...")
        cursor.execute("SHOW COLUMNS FROM customers LIKE 'status'")
        if not cursor.fetchone():
            print("Adding 'status' column...")
            cursor.execute("ALTER TABLE customers ADD COLUMN status VARCHAR(50) DEFAULT 'Tiềm năng' AFTER company")
            conn.commit()

        print("Migration successful (customers)!")

        # Tạo bảng audit_logs
        print("Checking for 'audit_logs' table...")
        cursor.execute("SHOW TABLES LIKE 'audit_logs'")
        if not cursor.fetchone():
            print("Creating 'audit_logs' table...")
            cursor.execute("""
                CREATE TABLE audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    action VARCHAR(50) NOT NULL,
                    target_table VARCHAR(50),
                    target_id INT,
                    old_value TEXT,
                    new_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("Migration successful (audit_logs)!")
        else:
            print("'audit_logs' table already exists.")

        # Thêm cột balance vào bảng customers
        print("Checking for 'balance' column in 'customers'...")
        cursor.execute("SHOW COLUMNS FROM customers LIKE 'balance'")
        if not cursor.fetchone():
            print("Adding 'balance' column...")
            cursor.execute("ALTER TABLE customers ADD COLUMN balance DECIMAL(15,2) DEFAULT 0 AFTER status")
            conn.commit()
            print("Migration successful (balance)!")

        # Thêm cột objective vào bảng campaigns
        print("Checking for 'objective' column in 'campaigns'...")
        cursor.execute("SHOW COLUMNS FROM campaigns LIKE 'objective'")
        if not cursor.fetchone():
            print("Adding 'objective' column...")
            cursor.execute("ALTER TABLE campaigns ADD COLUMN objective VARCHAR(255) AFTER name")
            conn.commit()
            print("Migration successful (objective)!")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
