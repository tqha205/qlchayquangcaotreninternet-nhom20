-- Tạo cơ sở dữ liệu
CREATE DATABASE IF NOT EXISTS ads_manager_db;
USE ads_manager_db;

-- 1. Bảng customers
CREATE TABLE IF NOT EXISTS customers (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255),
    phone       VARCHAR(20),
    address     TEXT,
    marketer_id INT DEFAULT NULL,         -- Nhân viên phụ trách
    is_deleted  TINYINT(1) DEFAULT 0,     -- Soft delete
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng users
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,
    role        ENUM('admin', 'marketer', 'client') NOT NULL,
    customer_id INT DEFAULT NULL,
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- Ràng buộc khóa ngoại cho customers (marketer_id -> users.id)
ALTER TABLE customers ADD CONSTRAINT fk_customer_marketer FOREIGN KEY (marketer_id) REFERENCES users(id) ON DELETE SET NULL;

-- 3. Bảng platforms (Tài khoản quảng cáo)
CREATE TABLE IF NOT EXISTS platforms (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,          -- e.g., Facebook Ads, Google Ads
    account_id  VARCHAR(100),                  -- ID tài khoản thật trên nền tảng
    status      ENUM('active', 'disconnected', 'error') DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Bảng campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    customer_id     INT,
    platform        VARCHAR(50),
    platform_id     INT DEFAULT NULL,              -- Liên kết tới bảng platforms
    target_link     VARCHAR(500),
    objective       VARCHAR(100),
    budget          DECIMAL(15, 2) DEFAULT 0,
    spent           DECIMAL(15, 2) DEFAULT 0,
    approval_status ENUM('pending', 'active', 'paused', 'completed') DEFAULT 'pending',
    status          VARCHAR(50) DEFAULT 'Đang chạy', -- Trạng thái hiển thị chung
    start_date      DATE,
    end_date        DATE,
    is_deleted      TINYINT(1) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    FOREIGN KEY (platform_id) REFERENCES platforms(id) ON DELETE SET NULL
);

-- 5. Bảng daily_spending
CREATE TABLE IF NOT EXISTS daily_spending (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id    INT NOT NULL,
    date           DATE NOT NULL,
    amount_spent   DECIMAL(15, 2) DEFAULT 0,
    clicks         INT DEFAULT 0,
    impressions    INT DEFAULT 0,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

-- 6. Bảng transactions (Giao dịch)
CREATE TABLE IF NOT EXISTS transactions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    customer_id    INT NOT NULL,
    type           ENUM('topup', 'deduction', 'refund') NOT NULL,
    amount         DECIMAL(15, 2) NOT NULL,
    description    TEXT,
    status         ENUM('pending', 'completed', 'failed') DEFAULT 'completed',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
);

-- 7. Bảng invoices (Hóa đơn)
CREATE TABLE IF NOT EXISTS invoices (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    customer_id    INT NOT NULL,
    invoice_number VARCHAR(100) NOT NULL,
    file_path      VARCHAR(500),
    issued_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
);

-- 8. Bảng notifications
CREATE TABLE IF NOT EXISTS notifications (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    title          VARCHAR(255) NOT NULL,
    message        TEXT,
    type           VARCHAR(50),
    is_read        TINYINT(1) DEFAULT 0,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 9. Bảng audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT,
    action         VARCHAR(100) NOT NULL,
    target_table   VARCHAR(100),
    target_id      INT,
    old_data       JSON,
    new_data       JSON,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 10. Bảng inquiries
CREATE TABLE IF NOT EXISTS inquiries (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    email      VARCHAR(255),
    phone      VARCHAR(20),
    service    VARCHAR(100),
    message    TEXT,
    status     ENUM('new', 'read', 'replied') DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DỮ LIỆU MẪU
INSERT INTO users (username, password, role) VALUES 
    ('admin', 'scrypt:32768:8:1$Qem5Q09wkvRP25Rz$d13ecf1ffbdf093ecf2542150e85abcbfbb0bf7b8fc36dd884842d24eeb6f1e772bbe21be81ee3e24c9bfdc65104fe929527753347af3499e0a0c94f9c6f1bca', 'admin'),
    ('marketer1', 'scrypt:32768:8:1$Qem5Q09wkvRP25Rz$d13ecf1ffbdf093ecf2542150e85abcbfbb0bf7b8fc36dd884842d24eeb6f1e772bbe21be81ee3e24c9bfdc65104fe929527753347af3499e0a0c94f9c6f1bca', 'marketer');

INSERT INTO platforms (name, account_id, status) VALUES 
    ('Facebook Ads', 'ACT_123456789', 'active'),
    ('Google Ads', '123-456-7890', 'active'),
    ('TikTok Ads', 'TT_987654321', 'active');

INSERT INTO customers (name, email, phone) VALUES 
    ('Công ty ABC',        'abc@company.vn', '0901234567'),
    ('Shop Thời Trang XYZ','xyz@shop.vn',    '0912345678');

INSERT INTO campaigns (name, customer_id, platform, budget, spent, approval_status, status, start_date, end_date) VALUES 
    ('Chiến dịch Mùa Hè',     1, 'Facebook', 10000000, 4500000, 'active', 'Đang chạy', '2025-06-01', '2025-08-31'),
    ('Quảng cáo Google Search',1, 'Google',   5000000,  1200000, 'active', 'Đang chạy', '2025-05-01', '2025-07-31'),
    ('TikTok Viral Trend',     2, 'TikTok',   8000000,  7500000, 'paused', 'Tạm dừng', '2025-04-01', '2025-06-30'),
    ('Zalo OA Khuyến mãi',     2, 'Zalo',     6000000,  3000000, 'active', 'Đang chạy', '2025-06-01', '2025-07-01'),
    ('Cốc Cốc Banner Mới',     1, 'Cốc Cốc',  4000000,   500000, 'pending', 'Chờ duyệt', '2025-06-15', '2025-08-15');

-- Giả lập chi tiêu
INSERT INTO daily_spending (campaign_id, date, amount_spent, clicks, impressions) VALUES 
    (1, '2025-06-01', 500000, 100, 5000),
    (1, '2025-06-02', 600000, 120, 5500),
    (2, '2025-05-01', 200000, 40,  1000);
