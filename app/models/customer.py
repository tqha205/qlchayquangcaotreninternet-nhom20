from .base import DBModel

class CustomerModel(DBModel):

    @staticmethod
    def get_all(marketer_id=None):
        """Lấy toàn bộ khách hàng kèm số chiến dịch (subquery)."""
        query = """
            SELECT
                c.id, c.name, c.email, c.phone, c.company, c.status, c.created_at, c.marketer_id,
                u.username AS marketer_name,
                (SELECT COUNT(*) FROM campaigns cam WHERE cam.customer_id = c.id AND cam.is_deleted = 0) AS total_campaigns,
                (SELECT COUNT(*) FROM campaigns cam
                    WHERE cam.customer_id = c.id AND cam.status = 'Đang chạy' AND cam.is_deleted = 0) AS active_campaigns,
                (SELECT COALESCE(SUM(cam.budget), 0)
                    FROM campaigns cam WHERE cam.customer_id = c.id AND cam.is_deleted = 0) AS total_budget
            FROM customers c
            LEFT JOIN users u ON c.marketer_id = u.id
            WHERE c.is_deleted = 0
        """
        params = []
        if marketer_id:
            query += " AND c.marketer_id = %s"
            params.append(marketer_id)
        
        query += " ORDER BY c.id DESC"
        
        rows = DBModel.fetch_all(query, params)
        for r in rows:
            r['total_budget'] = float(r.get('total_budget') or 0)
        return rows

    @staticmethod
    def get_by_id(customer_id):
        """Lấy thông tin một khách hàng bao gồm số dư."""
        return DBModel.fetch_one(
            "SELECT * FROM customers WHERE id = %s AND is_deleted = 0",
            (customer_id,)
        )

    @staticmethod
    def deposit(customer_id, amount):
        """Cộng tiền vào tài khoản khách hàng."""
        query = "UPDATE customers SET balance = balance + %s WHERE id = %s"
        return DBModel.execute(query, (amount, customer_id))

    @staticmethod
    def create(name, email=None, phone=None, company=None, status='Tiềm năng', marketer_id=None):
        """Thêm khách hàng mới. Trả về ID vừa tạo."""
        query = "INSERT INTO customers (name, email, phone, company, status, marketer_id) VALUES (%s, %s, %s, %s, %s, %s)"
        return DBModel.execute(query, (name, email, phone, company, status, marketer_id))

    @staticmethod
    def update(customer_id, name, email=None, phone=None, company=None, status=None, marketer_id=None):
        """Cập nhật thông tin khách hàng."""
        query = """
            UPDATE customers
            SET name=%s, email=%s, phone=%s, company=%s, status=%s, marketer_id=%s
            WHERE id=%s AND is_deleted = 0
        """
        return DBModel.execute(query, (name, email, phone, company, status, marketer_id, customer_id))

    @staticmethod
    def delete(customer_id):
        """Xóa khách hàng (Soft Delete)."""
        return DBModel.execute("UPDATE customers SET is_deleted = 1 WHERE id = %s", (customer_id,))
