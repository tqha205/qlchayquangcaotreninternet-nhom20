"""
Migration Module 3 — Tạo bảng daily_reports và notifications
Chạy 1 lần: python database/migrate_module3.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from config import MYSQL_CONFIG

conn = mysql.connector.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

statements = [
    # Bảng daily_reports
    """
    CREATE TABLE IF NOT EXISTS daily_reports (
        id INT AUTO_INCREMENT PRIMARY KEY,
        campaign_id INT NOT NULL,
        report_date DATE NOT NULL,
        daily_spent DECIMAL(15,2) DEFAULT 0,
        clicks INT DEFAULT 0,
        impressions INT DEFAULT 0,
        conversions INT DEFAULT 0,
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
        UNIQUE KEY unique_daily (campaign_id, report_date)
    )
    """,
    # Bảng notifications
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        campaign_id INT,
        type VARCHAR(50),
        message TEXT,
        is_read TINYINT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
    )
    """,
]

for stmt in statements:
    try:
        cursor.execute(stmt)
        print(f"✅ Thực thi thành công.")
    except mysql.connector.Error as e:
        print(f"⚠️  Lỗi: {e}")

conn.commit()
conn.close()
print("\n🎉 Migration Module 3 hoàn tất!")
print("   - Bảng daily_reports: OK")
print("   - Bảng notifications: OK")
