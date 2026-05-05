-- ========================================================
-- FULL DATABASE SETUP FOR ADS MANAGER SYSTEM
-- Version: 2.2 (Fix Encoding & Full Data)
-- ========================================================

SET NAMES 'utf8mb4';
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS ads_manager_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ads_manager_db;

-- Xóa các bảng cũ để làm mới hoàn toàn
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS daily_reports;
DROP TABLE IF EXISTS daily_spending;
DROP TABLE IF EXISTS creatives;
DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS platforms;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS inquiries;

SET FOREIGN_KEY_CHECKS = 1;

-- 1. Bảng customers (Quản lý thông tin khách hàng/doanh nghiệp)
CREATE TABLE customers (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    company     VARCHAR(255),
    email       VARCHAR(255),
    phone       VARCHAR(20),
    address     TEXT,
    status      VARCHAR(50) DEFAULT 'Tiềm năng',
    balance     DECIMAL(15, 2) DEFAULT 0,
    marketer_id INT DEFAULT NULL,
    is_deleted  TINYINT(1) DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Bảng users (Quản lý tài khoản đăng nhập)
CREATE TABLE users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,
    role        ENUM('admin', 'marketer', 'client') NOT NULL,
    customer_id INT DEFAULT NULL,
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Thêm ràng buộc cho customers (phải sau khi có bảng users)
ALTER TABLE customers ADD CONSTRAINT fk_customer_marketer FOREIGN KEY (marketer_id) REFERENCES users(id) ON DELETE SET NULL;

-- 3. Bảng platforms
CREATE TABLE platforms (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,
    account_id  VARCHAR(100),
    status      ENUM('active', 'disconnected', 'error') DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Bảng campaigns
CREATE TABLE campaigns (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    name             VARCHAR(255) NOT NULL,
    objective        VARCHAR(255),
    customer_id      INT,
    platform         VARCHAR(50),
    target_link      TEXT,
    platform_id      INT DEFAULT NULL,
    budget           DECIMAL(15, 2) DEFAULT 0,
    spent            DECIMAL(15, 2) DEFAULT 0,
    approval_status  ENUM('pending', 'active', 'paused', 'completed', 'rejected') DEFAULT 'pending',
    status           VARCHAR(50) DEFAULT 'Chờ duyệt',
    rejection_reason TEXT,
    start_date       DATE,
    end_date         DATE,
    is_deleted       TINYINT(1) DEFAULT 0,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    FOREIGN KEY (platform_id) REFERENCES platforms(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Bảng creatives
CREATE TABLE creatives (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id INT NOT NULL,
    name        VARCHAR(255) NOT NULL,
    media_type  VARCHAR(50) DEFAULT 'image',
    media_url   TEXT,
    content     TEXT,
    status      VARCHAR(50) DEFAULT 'Chờ duyệt',
    feedback    TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Bảng daily_reports
CREATE TABLE daily_reports (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id  INT NOT NULL,
    report_date  DATE NOT NULL,
    daily_spent  DECIMAL(15, 2) DEFAULT 0,
    clicks       INT DEFAULT 0,
    impressions  INT DEFAULT 0,
    conversions  INT DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    UNIQUE KEY unique_daily (campaign_id, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Bảng transactions
CREATE TABLE transactions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    customer_id    INT NOT NULL,
    type           ENUM('topup', 'deduction', 'refund') NOT NULL,
    amount         DECIMAL(15, 2) NOT NULL,
    description    TEXT,
    payment_method VARCHAR(100),
    proof_image    VARCHAR(500),
    status         ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    reject_reason  TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Bảng invoices
CREATE TABLE invoices (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    customer_id    INT NOT NULL,
    invoice_number VARCHAR(100) NOT NULL,
    file_path      VARCHAR(500),
    issued_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Bảng notifications
CREATE TABLE notifications (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT,
    campaign_id    INT DEFAULT NULL,
    title          VARCHAR(255) NOT NULL,
    message        TEXT,
    type           VARCHAR(50),
    is_read        TINYINT(1) DEFAULT 0,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Bảng audit_logs
CREATE TABLE audit_logs (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT,
    action         VARCHAR(100) NOT NULL,
    target_table   VARCHAR(100),
    target_id      INT,
    old_value      JSON,
    new_value      JSON,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Bảng inquiries
CREATE TABLE inquiries (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    email      VARCHAR(255),
    phone      VARCHAR(20),
    service    VARCHAR(100),
    message    TEXT,
    status     VARCHAR(50) DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- DỮ LIỆU MẪU (SAMPLE DATA)
-- ========================================================

-- Users (Mật khẩu: 123456)
INSERT INTO users (id, username, password, role) VALUES 
(1, 'admin', 'scrypt:32768:8:1$Qem5Q09wkvRP25Rz$d13ecf1ffbdf093ecf2542150e85abcbfbb0bf7b8fc36dd884842d24eeb6f1e772bbe21be81ee3e24c9bfdc65104fe929527753347af3499e0a0c94f9c6f1bca', 'admin'),
(2, 'marketer1', 'scrypt:32768:8:1$Qem5Q09wkvRP25Rz$d13ecf1ffbdf093ecf2542150e85abcbfbb0bf7b8fc36dd884842d24eeb6f1e772bbe21be81ee3e24c9bfdc65104fe929527753347af3499e0a0c94f9c6f1bca', 'marketer'),
(3, 'client1', 'scrypt:32768:8:1$Qem5Q09wkvRP25Rz$d13ecf1ffbdf093ecf2542150e85abcbfbb0bf7b8fc36dd884842d24eeb6f1e772bbe21be81ee3e24c9bfdc65104fe929527753347af3499e0a0c94f9c6f1bca', 'client');

-- Customers
INSERT INTO customers (id, name, company, email, phone, address, status, balance, marketer_id) VALUES 
(1, 'Nguyễn Văn A', 'Công ty Công nghệ ABC', 'vana@gmail.com', '0901234567', '123 Cách Mạng Tháng 8, HCM', 'Đang hợp tác', 5000000.00, 2),
(2, 'Trần Thị B', 'Shop Thời trang XYZ', 'tranthib@gmail.com', '0912345678', '456 Lê Lợi, Đà Nẵng', 'Tiềm năng', 0.00, 2);

-- Gắn client1 vào customer 1
UPDATE users SET customer_id = 1 WHERE id = 3;

-- Platforms
INSERT INTO platforms (id, name, account_id, status) VALUES 
(1, 'Facebook Ads', 'ACT_FB_888999', 'active'),
(2, 'Google Ads', '999-111-222', 'active'),
(3, 'TikTok Ads', 'TT_ADS_777', 'active');

-- Campaigns
INSERT INTO campaigns (id, name, objective, customer_id, platform, target_link, platform_id, budget, spent, approval_status, status, start_date, end_date) VALUES 
(1, 'Chiến dịch Mùa Hè 2024', 'Lượt Click', 1, 'Facebook', 'https://abc.com/summer', 1, 10000000.00, 2500000.00, 'active', 'Đang chạy', '2024-06-01', '2024-08-31'),
(2, 'Quảng cáo Search Website', 'Chuyển đổi', 1, 'Google', 'https://abc.com/service', 2, 5000000.00, 1200000.00, 'active', 'Đang chạy', '2024-05-15', '2024-07-15'),
(3, 'Viral Video TikTok', 'Tương tác', 2, 'TikTok', 'https://xyz.com/viral', 3, 3000000.00, 0.00, 'pending', 'Chờ duyệt', '2024-07-01', '2024-07-30');

-- Creatives
INSERT INTO creatives (id, campaign_id, name, media_type, media_url, content, status) VALUES 
(1, 1, 'Banner Sale 50%', 'image', 'https://img.com/banner1.jpg', 'Siêu sale mùa hè, giảm ngay 50% tất cả mặt hàng!', 'Đã duyệt'),
(2, 1, 'Video Review Sản phẩm', 'video', 'https://vid.com/review1.mp4', 'Xem ngay video review cực chất.', 'Đã duyệt'),
(3, 3, 'TikTok Clip Dance', 'video', 'https://vid.com/dance1.mp4', 'Tham gia thử thách cùng Shop XYZ!', 'Chờ duyệt');

-- Daily Reports
INSERT INTO daily_reports (campaign_id, report_date, daily_spent, clicks, impressions, conversions) VALUES 
(1, '2024-06-01', 500000.00, 120, 5000, 10),
(1, '2024-06-02', 600000.00, 150, 6200, 15),
(2, '2024-05-15', 200000.00, 45, 1000, 2);

-- Transactions
INSERT INTO transactions (id, customer_id, type, amount, description, payment_method, proof_image, status) VALUES 
(1, 1, 'topup', 5000000.00, 'Nạp tiền đợt 1 tháng 6', 'Chuyển khoản Ngân hàng', '/static/uploads/proofs/proof1.jpg', 'completed'),
(2, 1, 'topup', 2000000.00, 'Nạp thêm ngân sách Google', 'MoMo', '/static/uploads/proofs/proof2.jpg', 'pending');

-- Invoices
INSERT INTO invoices (transaction_id, customer_id, invoice_number, file_path) VALUES 
(1, 1, 'INV-20240601-001', '/static/uploads/invoices/inv1.pdf');

-- Notifications
INSERT INTO notifications (user_id, campaign_id, title, message, type) VALUES 
(1, 3, 'Yêu cầu duyệt chiến dịch', 'Khách hàng Trần Thị B vừa tạo chiến dịch mới.', 'info'),
(3, 1, 'Chiến dịch đã hoạt động', 'Chiến dịch Mùa Hè 2024 của bạn đã được Admin phê duyệt.', 'success');

-- Inquiries
INSERT INTO inquiries (name, email, phone, service, message, status) VALUES 
('Lê Văn Luyện', 'luyen@gmail.com', '0988777666', 'Facebook Ads', 'Tôi muốn tư vấn gói quảng cáo Fanpage.', 'new');
