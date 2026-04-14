# =============================================
# TÀI LIỆU TUẦN 2 – XÂY DỰNG FRONTEND PYQT5
# =============================================

## 1. LỰA CHỌN CÔNG NGHỆ

### So sánh PyQt5 vs Tkinter

| Tiêu chí | Tkinter | **PyQt5 ✅** |
|---|---|---|
| Giao diện | Cũ, không thể tùy biến nhiều | Hiện đại, hỗ trợ CSS Stylesheet |
| Bộ Widget | Cơ bản | Phong phú (Table, Stack, Combo, ...) |
| Qt Designer | Không | Có – Kéo thả, xuất .ui → .py |
| Cộng đồng | Trung bình | Rất lớn |

**Chọn: PyQt5** – Vì giao diện đẹp, có QStackedWidget (chuyển trang không cần mở thêm cửa sổ), styles CSS mạnh mẽ.

---

## 2. CẤU TRÚC FILE

```
src/views/
├── login.py        # Màn hình đăng nhập (2 cột, validate)
└── dashboard.py    # Dashboard trung tâm (Sidebar + 4 trang)
main.py             # Entry point
```

---

## 3. MÔ TẢ CÁC MÀN HÌNH

### a. Login Form (`login.py`)
- Layout 2 cột: Trái = Banner gradient xanh Navy / Phải = Form trắng
- Validate: Bỏ trống báo lỗi đỏ ngay trên giao diện (không dùng Popup)  
- 2 tài khoản demo: `admin/admin123` và `marketer/mk123`
- Sau khi đăng nhập, truyền `username` và `role` sang Dashboard

### b. Dashboard (`dashboard.py`) – 4 Trang chính
Sử dụng `QStackedWidget` để chuyển trang mượt mà (không mở cửa sổ mới).

| Trang | Nội dung |
|---|---|
| Tổng quan | 4 thẻ KPI + Bảng Top 5 chiến dịch hiệu quả |
| Chiến dịch | CRUD đầy đủ + Tìm kiếm realtime + màu trạng thái |
| Khách hàng | CRUD đầy đủ + Tìm kiếm realtime |
| Báo cáo | 3 thẻ KPI + Bảng theo nền tảng + Biểu đồ phân bổ ngân sách |

---

## 4. HƯỚNG DẪN CHẠY

```bash
# 1. Cài thư viện
pip install PyQt5

# 2. Chạy từ thư mục gốc dự án
python main.py
```

Luồng: Login (admin/admin123) → Đóng form login → Dashboard mở ra → Dùng Sidebar để điều hướng giữa các trang.

---

## 5. BONUS – TÍCH HỢP QT DESIGNER

```bash
# Sau khi kéo thả giao diện xong trong Qt Designer, lưu file .ui
# Convert sang Python:
pyuic5 -x dashboard.ui -o dashboard.py

# Hoặc load động trong code:
from PyQt5 import uic
uic.loadUi('dashboard.ui', self)
```
