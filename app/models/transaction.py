from .base import DBModel

class TransactionModel(DBModel):
    """Model quản lý nạp tiền, trừ tiền và hóa đơn."""

    @staticmethod
    def get_by_customer(customer_id):
        sql = "SELECT * FROM transactions WHERE customer_id = %s ORDER BY created_at DESC"
        return DBModel.fetch_all(sql, (customer_id,))

    @staticmethod
    def create_transaction(customer_id, t_type, amount, description='', payment_method=None, proof_image=None, status='pending'):
        """Tạo giao dịch."""
        sql = """
            INSERT INTO transactions (customer_id, type, amount, description, payment_method, proof_image, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return DBModel.execute(sql, (customer_id, t_type, amount, description, payment_method, proof_image, status))

    @staticmethod
    def get_all(customer_id=None, status=None):
        sql = """
            SELECT t.*, c.name as customer_name 
            FROM transactions t
            JOIN customers c ON t.customer_id = c.id
            WHERE 1=1
        """
        params = []
        if customer_id:
            sql += " AND t.customer_id = %s"
            params.append(customer_id)
        if status:
            sql += " AND t.status = %s"
            params.append(status)
        
        sql += " ORDER BY t.created_at DESC"
        return DBModel.fetch_all(sql, tuple(params) if params else None)

    @staticmethod
    def get_by_id(transaction_id):
        sql = "SELECT * FROM transactions WHERE id = %s"
        return DBModel.fetch_one(sql, (transaction_id,))

    @staticmethod
    def update_status(transaction_id, status, reject_reason=None):
        sql = "UPDATE transactions SET status = %s, reject_reason = %s WHERE id = %s"
        return DBModel.execute(sql, (status, reject_reason, transaction_id))

    @staticmethod
    def get_invoices(customer_id):
        sql = "SELECT * FROM invoices WHERE customer_id = %s ORDER BY issued_at DESC"
        return DBModel.fetch_all(sql, (customer_id,))
