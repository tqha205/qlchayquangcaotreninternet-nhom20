-- ============================================================
-- MIGRATION: Multi-Platform Campaign Support
-- Tính năng: 1 chiến dịch → nhiều nền tảng
--            Theo dõi kết quả theo từng nền tảng
--            Trạng thái thanh toán của chiến dịch
-- ============================================================

USE ads_manager_db;

-- 1. Bảng campaign_platforms (many-to-many: campaign ↔ platform)
CREATE TABLE IF NOT EXISTS campaign_platforms (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    campaign_id  INT NOT NULL,
    platform_id  INT NOT NULL,
    budget_alloc DECIMAL(15,2) DEFAULT 0,   -- Ngân sách phân bổ riêng cho nền tảng
    spent        DECIMAL(15,2) DEFAULT 0,   -- Chi tiêu tích lũy trên nền tảng
    status       ENUM('active','paused','completed') DEFAULT 'active',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (platform_id) REFERENCES platforms(id) ON DELETE RESTRICT,
    UNIQUE KEY uq_camp_plat (campaign_id, platform_id)
);

-- 2. Thêm cột platform_id vào daily_spending (gắn chi tiêu theo nền tảng)
ALTER TABLE daily_spending 
    ADD COLUMN IF NOT EXISTS camp_platform_id INT DEFAULT NULL,
    ADD CONSTRAINT fk_ds_camp_plat FOREIGN KEY (camp_platform_id) 
        REFERENCES campaign_platforms(id) ON DELETE SET NULL;

-- 3. Thêm trạng thái thanh toán vào bảng campaigns
ALTER TABLE campaigns 
    ADD COLUMN IF NOT EXISTS payment_status ENUM('paid','underfunded','pending') DEFAULT 'pending';

-- 4. Di chuyển dữ liệu cũ: tạo bản ghi campaign_platforms cho các campaign đã có platform
-- (Chỉ chạy nếu bảng platforms đã có dữ liệu)
INSERT IGNORE INTO campaign_platforms (campaign_id, platform_id, budget_alloc, spent, status)
SELECT 
    c.id AS campaign_id,
    p.id AS platform_id,
    c.budget AS budget_alloc,
    c.spent AS spent,
    CASE c.approval_status
        WHEN 'active' THEN 'active'
        WHEN 'paused' THEN 'paused'
        WHEN 'completed' THEN 'completed'
        ELSE 'active'
    END AS status
FROM campaigns c
JOIN platforms p ON p.name LIKE CONCAT(c.platform, '%')
WHERE c.is_deleted = 0 AND c.platform IS NOT NULL AND c.platform != '';

-- 5. Xem kết quả migration
SELECT 
    c.name AS campaign_name,
    p.name AS platform_name,
    cp.budget_alloc,
    cp.spent,
    cp.status
FROM campaign_platforms cp
JOIN campaigns c ON cp.campaign_id = c.id
JOIN platforms p ON cp.platform_id = p.id
ORDER BY c.id;
