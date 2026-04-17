import mysql.connector
from config import MYSQL_CONFIG

class DBModel:
    @staticmethod
    def get_conn():
        return mysql.connector.connect(**MYSQL_CONFIG)

    @staticmethod
    def fetch_all(query, params=None):
        conn = DBModel.get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        res = cursor.fetchall()
        conn.close()
        return res

    @staticmethod
    def fetch_one(query, params=None):
        conn = DBModel.get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        res = cursor.fetchone()
        conn.close()
        return res

    @staticmethod
    def execute(query, params=None):
        conn = DBModel.get_conn()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

# Các hàm helper cho các Model cụ thể
class UserModel(DBModel):
    @staticmethod
    def get_by_auth(username, password):
        return DBModel.fetch_one("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))

    @staticmethod
    def create_client(username, password, full_name, email=None, phone=None):
        # 1. Tạo khách hàng trước
        cust_query = "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)"
        cust_id = DBModel.execute(cust_query, (full_name, email, phone))
        
        # 2. Tạo user liên kết với khách hàng đó
        user_query = "INSERT INTO users (username, password, role, customer_id) VALUES (%s, %s, %s, %s)"
        return DBModel.execute(user_query, (username, password, 'client', cust_id))

class CampaignModel(DBModel):
    @staticmethod
    def get_by_role(role, customer_id=None):
        query = "SELECT c.*, cust.name as customer_name FROM campaigns c LEFT JOIN customers cust ON c.customer_id = cust.id"
        if role == 'client' and customer_id:
            query += " WHERE c.customer_id = %s"
            return DBModel.fetch_all(query, (customer_id,))
        return DBModel.fetch_all(query)

class InquiryModel(DBModel):
    @staticmethod
    def create(data):
        query = "INSERT INTO inquiries (name, email, phone, service, message) VALUES (%s, %s, %s, %s, %s)"
        return DBModel.execute(query, (data['name'], data['email'], data['phone'], data['service'], data['message']))
