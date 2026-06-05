import pymysql
import os

connection = pymysql.connect(
    host='localhost',
    user='root',
    password='',
    database='ads_manager_db',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        cursor.execute("ALTER TABLE transactions ADD COLUMN balance_after DECIMAL(18,2) DEFAULT NULL;")
        cursor.execute("ALTER TABLE transactions ADD COLUMN campaign_id INT DEFAULT NULL;")
        cursor.execute("ALTER TABLE transactions ADD CONSTRAINT fk_trans_campaign FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL;")
        print("Columns added successfully.")
except Exception as e:
    print(f"Error: {e}")
finally:
    connection.commit()
    connection.close()
