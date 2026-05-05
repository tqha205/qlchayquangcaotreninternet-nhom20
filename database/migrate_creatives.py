import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from config import MYSQL_CONFIG

def migrate():
    print("--- MIGRATION: ADDING CREATIVES TABLE ---")
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        print("Checking for 'creatives' table...")
        cursor.execute("SHOW TABLES LIKE 'creatives'")
        if not cursor.fetchone():
            print("Creating 'creatives' table...")
            cursor.execute("""
                CREATE TABLE creatives (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    campaign_id INT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    media_type VARCHAR(50) DEFAULT 'image',
                    media_url TEXT,
                    content TEXT,
                    status VARCHAR(50) DEFAULT 'Chờ duyệt',
                    feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            print("Migration successful (creatives)!")
        else:
            print("'creatives' table already exists.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
