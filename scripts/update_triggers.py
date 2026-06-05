import pymysql

connection = pymysql.connect(host='localhost', user='root', password='', database='ads_manager_db')

trigger1 = """
CREATE TRIGGER after_daily_spending_insert
AFTER INSERT ON daily_spending
FOR EACH ROW
BEGIN
    DECLARE cust_id INT;
    DECLARE campaign_name VARCHAR(255);
    DECLARE current_balance DECIMAL(18,2);
    DECLARE b_after DECIMAL(18,2);
    
    SELECT customer_id, name INTO cust_id, campaign_name 
    FROM campaigns WHERE id = NEW.campaign_id;
    
    IF cust_id IS NOT NULL AND NEW.amount_spent > 0 THEN
        SELECT balance INTO current_balance FROM customers WHERE id = cust_id;
        SET b_after = current_balance - NEW.amount_spent;
        
        UPDATE customers SET balance = b_after WHERE id = cust_id;
        
        INSERT INTO transactions (customer_id, type, amount, description, payment_method, status, created_at, balance_after, campaign_id)
        VALUES (
            cust_id, 'deduction', NEW.amount_spent, 
            CONCAT('Trừ phí tự động chiến dịch: ', campaign_name, ' (Ngày ', DATE_FORMAT(NEW.date, '%d/%m/%Y'), ')'),
            'Hệ thống trừ tự động', 'completed', NOW(), b_after, NEW.campaign_id
        );
    END IF;
END
"""

trigger2 = """
CREATE TRIGGER after_daily_spending_update
AFTER UPDATE ON daily_spending
FOR EACH ROW
BEGIN
    DECLARE cust_id INT;
    DECLARE campaign_name VARCHAR(255);
    DECLARE diff_spent DECIMAL(15, 2);
    DECLARE current_balance DECIMAL(18,2);
    DECLARE b_after DECIMAL(18,2);
    
    SET diff_spent = NEW.amount_spent - OLD.amount_spent;
    
    IF diff_spent > 0 THEN
        SELECT customer_id, name INTO cust_id, campaign_name 
        FROM campaigns WHERE id = NEW.campaign_id;
        
        IF cust_id IS NOT NULL THEN
            SELECT balance INTO current_balance FROM customers WHERE id = cust_id;
            SET b_after = current_balance - diff_spent;
            
            UPDATE customers SET balance = b_after WHERE id = cust_id;
            
            INSERT INTO transactions (customer_id, type, amount, description, payment_method, status, created_at, balance_after, campaign_id)
            VALUES (
                cust_id, 'deduction', diff_spent, 
                CONCAT('Trừ phí bổ sung chiến dịch: ', campaign_name, ' (Ngày ', DATE_FORMAT(NEW.date, '%d/%m/%Y'), ')'),
                'Hệ thống trừ tự động', 'completed', NOW(), b_after, NEW.campaign_id
            );
        END IF;
    END IF;
END
"""

try:
    with connection.cursor() as cursor:
        cursor.execute("DROP TRIGGER IF EXISTS after_daily_spending_insert;")
        cursor.execute("DROP TRIGGER IF EXISTS after_daily_spending_update;")
        cursor.execute(trigger1)
        cursor.execute(trigger2)
        print("Triggers updated successfully with balance_after and campaign_id.")
finally:
    connection.commit()
    connection.close()
