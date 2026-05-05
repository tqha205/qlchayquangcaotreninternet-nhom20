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
