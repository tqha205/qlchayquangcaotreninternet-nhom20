-- Tạo cơ sở dữ liệu
CREATE DATABASE IF NOT EXISTS ads_manager_db;
USE ads_manager_db;

-- Bảng customers
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'marketer', 'client') NOT NULL,
    customer_id INT,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- Bảng campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    customer_id INT,
    platform VARCHAR(50), -- Facebook, Google, TikTok...
    budget DECIMAL(15, 2) DEFAULT 0,
    spent DECIMAL(15, 2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'Đang chạy',
    start_date DATE,
    end_date DATE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Bảng inquiries (Liên hệ từ trang Public)
CREATE TABLE IF NOT EXISTS inquiries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    service VARCHAR(100),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chèn dữ liệu mẫu
INSERT INTO customers (name) VALUES ('Công ty ABC'), ('Shop Thời Trang XYZ');

INSERT INTO users (username, password, role, customer_id) VALUES 
('admin', 'admin123', 'admin', NULL),
('marketer', 'mk123', 'marketer', NULL),
('client', 'client123', 'client', 1);

INSERT INTO campaigns (name, customer_id, platform, budget, spent, status) VALUES 
('Chiến dịch Mùa Hè', 1, 'Facebook', 10000000, 4500000, 'Đang chạy'),
('Quảng cáo Google Search', 1, 'Google', 5000000, 1200000, 'Đang chạy'),
('TikTok Viral Trend', 2, 'TikTok', 8000000, 7500000, 'Tạm dừng');
