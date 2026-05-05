from .base import DBModel
import mysql.connector
from config import MYSQL_CONFIG

class InquiryModel(DBModel):

    @staticmethod
    def create(data):
        """Lưu yêu cầu tư vấn mới từ trang public."""
        query = "INSERT INTO inquiries (name, email, phone, service, message) VALUES (%s, %s, %s, %s, %s)"
        return DBModel.execute(query, (data['name'], data['email'], data['phone'], data['service'], data['message']))

    @staticmethod
    def get_all():
        """Lấy toàn bộ danh sách yêu cầu tư vấn, mới nhất trước."""
        return DBModel.fetch_all(
            "SELECT * FROM inquiries ORDER BY created_at DESC"
        )

    @staticmethod
    def get_by_status(status):
        """Lấy inquiries theo trạng thái: 'new', 'read', 'replied'."""
        return DBModel.fetch_all(
            "SELECT * FROM inquiries WHERE status = %s ORDER BY created_at DESC",
            (status,)
        )

    @staticmethod
    def mark_read(inquiry_id):
        """Đánh dấu yêu cầu đã đọc."""
        return DBModel.execute(
            "UPDATE inquiries SET status = 'read' WHERE id = %s AND status = 'new'",
            (inquiry_id,)
        )

    @staticmethod
    def approve(inquiry_id):
        """
        Phê duyệt yêu cầu tư vấn → chuyển thành Khách hàng chính thức.
        - Tạo bản ghi mới trong bảng customers
        - Cập nhật inquiry.status = 'replied'
        - Trả về customer_id mới tạo, hoặc None nếu thất bại.
        """
        inquiry = DBModel.fetch_one("SELECT * FROM inquiries WHERE id = %s", (inquiry_id,))
        if not inquiry:
            return None

        conn   = None
        try:
            conn   = mysql.connector.connect(**MYSQL_CONFIG)
            cursor = conn.cursor()

            # 1. Tạo customer mới từ dữ liệu inquiry
            cursor.execute(
                "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)",
                (inquiry['name'], inquiry['email'], inquiry['phone'])
            )
            customer_id = cursor.lastrowid

            # 2. Cập nhật trạng thái inquiry
            cursor.execute(
                "UPDATE inquiries SET status = 'replied' WHERE id = %s",
                (inquiry_id,)
            )

            conn.commit()
            return customer_id

        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

