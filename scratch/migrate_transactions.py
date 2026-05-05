import mysql.connector

MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'ads_manager_db'
}

def migrate():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SHOW COLUMNS FROM transactions LIKE 'proof_image'")
        if not cursor.fetchone():
            print("Adding columns to transactions table...")
            cursor.execute("ALTER TABLE transactions ADD COLUMN proof_image VARCHAR(500) AFTER description")
            cursor.execute("ALTER TABLE transactions ADD COLUMN payment_method VARCHAR(100) AFTER type")
            cursor.execute("ALTER TABLE transactions ADD COLUMN reject_reason TEXT AFTER status")
            cursor.execute("ALTER TABLE transactions MODIFY COLUMN status ENUM('pending', 'completed', 'rejected') DEFAULT 'pending'")
            print("Migration successful.")
        else:
            print("Columns already exist.")
            
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
