#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để import database SQL và reset mật khẩu
"""

import mysql.connector
from mysql.connector import Error
import os
import sys
from config import MYSQL_CONFIG

def run_sql_file(sql_file_path):
    """Import SQL file vào database"""
    try:
        # Kết nối MySQL (không có database cụ thể để create DB)
        conn = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password']
        )
        cursor = conn.cursor()
        
        # Đọc file SQL
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Thực thi từng statement
        for statement in sql_content.split(';'):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✓ Database đã được import thành công từ {sql_file_path}")
        return True
        
    except Error as e:
        print(f"✗ Lỗi khi import database: {e}")
        return False

def reset_passwords():
    """Reset mật khẩu sang 123456 cho tất cả user"""
    try:
        sys.path.insert(0, '.')
        from app.models import UserModel
        
        users_to_reset = [
            (1, 'admin'),
            (2, 'marketer1'),
            (3, 'client1')
        ]
        
        for user_id, username in users_to_reset:
            success = UserModel.update(user_id, password='123456')
            status = "✓" if success else "✗"
            print(f"{status} Reset mật khẩu cho {username} (ID: {user_id}) → 123456")
        
        return True
        
    except Exception as e:
        print(f"✗ Lỗi khi reset password: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("SETUP DATABASE VÀ RESET MẬT KHẨU")
    print("=" * 60)
    
    # Bước 1: Import SQL
    print("\n[Bước 1] Import database SQL...")
    sql_path = os.path.join(os.path.dirname(__file__), 'database', 'full_database_setup.sql')
    if not run_sql_file(sql_path):
        sys.exit(1)
    
    # Bước 2: Reset mật khẩu
    print("\n[Bước 2] Reset mật khẩu người dùng...")
    if not reset_passwords():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ SETUP HOÀN TẤT!")
    print("=" * 60)
    print("\nBạn có thể đăng nhập với:")
    print("  Admin     : admin / 123456")
    print("  Marketer  : marketer1 / 123456")
    print("  Client    : client1 / 123456")
    print("\nChạy: python run.py")
