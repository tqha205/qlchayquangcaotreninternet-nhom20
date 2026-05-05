<div align="center">

# 📢 ADS Manager — Phần mềm Quản lý Dịch vụ Chạy Quảng cáo Online

**Hệ thống quản lý chiến dịch quảng cáo đa nền tảng, phân quyền người dùng và theo dõi ngân sách theo thời gian thực.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.x-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)
![Status](https://img.shields.io/badge/Trạng_thái-Hoàn_thành-success?style=for-the-badge)

</div>

---

## 📘 Giới thiệu

Dự án **ADS Manager** được xây dựng nhằm hỗ trợ các cá nhân và doanh nghiệp cung cấp dịch vụ quảng cáo quản lý toàn bộ vòng đời chiến dịch — từ tiếp nhận khách hàng, lập ngân sách, theo dõi hiệu quả đến lập báo cáo — một cách tập trung, nhanh chóng và chính xác.

| 🎯 Tính năng | 📖 Mô tả |
|---|---|
| 👤 Quản lý khách hàng | Thêm, sửa, xóa thông tin khách hàng và phê duyệt yêu cầu tư vấn |
| 📣 Quản lý chiến dịch | Theo dõi chiến dịch Facebook, Google, TikTok,... với CRUD đầy đủ |
| 💰 Kiểm soát ngân sách | Ghi nhận chi phí hàng ngày và cảnh báo tự động khi sắp hết ngân sách |
| 📊 Thống kê & Biểu đồ | Dashboard động với ApexCharts (Spending Trend, Platform Distribution) |
| 🔐 Phân quyền RBAC | Admin / Marketer / Client với giao diện và quyền truy cập API riêng biệt |
| 📄 Báo cáo | Xuất báo cáo chi tiết theo kỳ (PDF / Excel) với định dạng chuyên nghiệp |

---

## 👥 Thành viên nhóm (Nhóm 20)

| Họ và tên | MSSV | Vai trò |
|---|---|---|
| **Tạ Quang Hà** | ... | Trưởng nhóm (Leader) — Backend, Database, RBAC |
| **Nguyễn Hữu Tú** | ... | Thành viên — Frontend, UI/UX, Templates |
| **Nguyễn Quốc Dũng** | ... | Thành viên — Analytics, Reports, Testing |

---

## 🛠️ Công nghệ sử dụng

| Layer | Công nghệ |
|---|---|
| **Backend** | Python 3.10+, Flask 3.x, Werkzeug (Security) |
| **Database** | MySQL 8.0, mysql-connector-python |
| **Frontend** | HTML5, Tailwind CSS (CDN), Vanilla JS, Lucide Icons |
| **Charts** | ApexCharts (Đồ thị tương tác) |
| **Exports** | `openpyxl` (Excel), `reportlab` (PDF) |

---

## 📂 Cấu trúc thư mục thực tế

```
software_chay_quang_cao_online/
├── app/
│   ├── __init__.py              # Khấu tạo Flask app & Đăng ký Blueprints
│   ├── controllers/
│   │   ├── admin_controller.py  # Quản lý Campaign, Customer, Inquiry API
│   │   ├── auth_controller.py   # Login, Register, Logout (Session)
│   │   ├── public_controller.py # Website Landing Page
│   │   └── reports_controller.py # Export Excel/PDF & Report API
│   ├── models/
│   │   ├── base.py              # DBModel — CRUD helpers cho MySQL
│   │   ├── user.py              # UserModel — Auth logic
│   │   ├── campaign.py          # CampaignModel
│   │   ├── customer.py          # CustomerModel
│   │   ├── inquiry.py           # InquiryModel
│   │   ├── daily_report.py      # DailyReportModel (Module 3)
│   │   └── notification.py      # NotificationModel (Module 3)
│   ├── templates/
│   │   ├── layouts/             # admin_base.html (Sidebar, Notif UI)
│   │   ├── admin/               # dashboard.html, campaigns.html, customers.html, reports.html
│   │   ├── auth/                # login.html, register.html
│   │   └── public/              # index.html, contact.html
├── database/
│   ├── init_db.sql              # Schema MySQL cơ bản
│   ├── migrate_phase1.py        # Migration User/Campaign (password hash)
│   ├── migrate_module3.py       # Migration Daily Reports & Notifications
│   └── seed_hashed.py           # Dữ liệu mẫu (Password: Admin@123, ...)
├── config.py                    # Cấu hình DB & Flask Secret
├── run.py                       # File khởi chạy ứng dụng
└── requirements.txt             # Danh sách thư viện (pip install -r)
```

---

## ⚙️ Cài đặt & Khởi chạy

### 1. Clone & Cài đặt môi trường

```bash
git clone https://github.com/<your-org>/qlchayquangcaotreninternet-nhom20.git
cd qlchayquangcaotreninternet-nhom20
python -v venv venv
source venv/bin/activate  # Hoặc venv\Scripts\activate trên Windows
pip install -r requirements.txt
```

### 2. Cấu hình Database

Tạo database `ads_manager_db` trong MySQL và cấu hình lại file `config.py` nếu cần.

### 3. Setup Database (Quan trọng)

Chạy lần lượt các script sau để khởi tạo dữ liệu:

```bash
# 1. Nhập Schema SQL (Dùng phpMyAdmin Import hoặc Command Line)
mysql -u root -p ads_manager_db < database/init_db.sql

# 2. Chạy Migrations
python database/migrate_module3.py

# 3. Nạp dữ liệu mẫu
python database/seed_hashed.py
```

### 4. Chạy ứng dụng

```bash
python run.py
```

Truy cập: **http://localhost:5000**

---

## 📋 Tài khoản mặc định (Test)

| Username | Password | Role | Quyền hạn |
|---|---|---|---|
| `admin` | `Admin@123` | **Admin** | Toàn quyền hệ thống, Xóa dữ liệu |
| `marketer` | `Mark@123` | **Marketer** | Quản lý Campaign/Customer, Xem báo cáo |
| `client` | `Client@123` | **Client** | Chỉ xem Campaign & Dashboard cá nhân |

---

## ⭐ Các chức năng đã hoàn thiện

### 🟢 Module 1 & 2: Quản lý & RBAC
- **Phân quyền chặt chẽ:** Admin vs Client.
- **Inquiry Workflow:** Tiếp nhận yêu cầu từ Landing Page → Phê duyệt thành khách hàng chính thức.
- **Campaign CRUD:** Quản lý chiến dịch với validation (ngày bắt đầu < kết thúc, ngân sách > 0).

### 🟡 Module 3: Ngân sách & Cảnh báo (Real-time)
- **Daily Spending:** Ghi nhận chi phí phát sinh hàng ngày.
- **Auto-Paused:** Tự động tạm dừng chiến dịch khi `spent >= budget`.
- **Hệ thống Notification:** Thông báo Real-time trên sidebar (Bell icon) khi ngân sách vượt ngưỡng 90%.

### 🔵 Module 4: Analytics Dashboard
- **ApexCharts:** Biểu đồ đường (Xu hướng chi phí), Biểu đồ tròn (Phân bổ nền tảng), Biểu đồ cột (Trạng thái).
- **KPI CountUp:** Hiệu ứng nhảy số khi tải Dashboard.
- **Top 5 Campaigns:** Bảng vinh danh các chiến dịch có chi tiêu lớn nhất.

### 🔴 Module 5: Báo cáo & Xuất file
- **Date Range Filter:** Lọc báo cáo theo khoảng thời gian bất kỳ.
- **Export Excel:** File đa sheet (Tổng hợp & Chi tiết) định dạng chuyên nghiệp.
- **Export PDF:** Báo cáo có bảng biểu rõ ràng dùng cho gửi khách hàng.

---

## 📅 Lộ trình phát triển đã thực hiện

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| **P1: Foundation** | Thiết kế CSDL (ERD) & Cấu trúc Flask MVC | ✅ Hoàn thành |
| **P2: Auth & RBAC** | Password Hashing (Werkzeug) & Middleware phân quyền | ✅ Hoàn thành |
| **P3: Campaign CRUD**| Quản lý chiến dịch & Khách hàng | ✅ Hoàn thành |
| **P4: Budget & Notif**| Log chi phí hàng ngày & Cảnh báo tự động | ✅ Hoàn thành |
| **P5: Data Visual** | Dashboard (ApexCharts) & Reports (Excel/PDF) | ✅ Hoàn thành |

---

## 📜 Quy tắc làm việc nhóm

| Quy tắc | Mô tả |
|---|---|
| ❌ **Không push thẳng vào `main`** | Luôn làm việc trên branch riêng |
| 🌿 **Đặt tên branch chuẩn** | `feature/ten-chuc-nang`, `fix/ten-loi`, `docs/ten-tai-lieu` |
| 🔁 **Pull Request bắt buộc** | Tạo PR và mô tả rõ thay đổi trước khi merge |
| ✅ **Commit có ý nghĩa** | `feat:`, `fix:`, `docs:`, `refactor:`, `test:` |
| 🔍 **Review chéo** | Ít nhất 1 thành viên khác review trước khi merge |

### Ví dụ commit message chuẩn:
```
feat: thêm chức năng đăng ký khách hàng
fix: sửa lỗi xác thực mật khẩu hash
docs: cập nhật README và sơ đồ ERD
refactor: tách require_role thành 2 decorator riêng
```

---

## 🤝 Đóng góp

1. Fork repository
2. Tạo branch: `git checkout -b feature/ten-chuc-nang`
3. Commit: `git commit -m 'feat: mô tả thay đổi'`
4. Push: `git push origin feature/ten-chuc-nang`
5. Tạo Pull Request

---

<div align="center">

**Nhóm 20 — Môn Phát triển Phần mềm Hướng Đối tượng**  
🏫 Được phát triển với ❤️ bởi Nhóm 20

</div>
