# TÀI LIỆU PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG
**Dự án:** Phần mềm quản lý dịch vụ chạy quảng cáo trực tuyến

## 1. PHÂN TÍCH CHỨC NĂNG HỆ THỐNG

### 1.1 Xác định các Actor
*   **Admin (Quản trị viên):** Người có toàn quyền quản lý tài khoản, xem thống kê hệ thống.
*   **Nhân viên Marketing (Marketer):** Gắn kết nền tảng, tạo chiến dịch và theo dõi ngân sách quảng cáo khách hàng.
*   **Khách hàng (Client):** Xem báo cáo, tình trạng phân bổ ngân sách.

### 1.2 Các chức năng chính
1. Quản lý tài khoản (Đăng ký, Đăng nhập, Phân quyền)
2. Quản lý khách hàng (Thêm/Sửa/Xóa Profile doanh nghiệp)
3. Quản lý chiến dịch quảng cáo (Lên camp, cấu hình ngân sách)
4. Quản lý nền tảng quảng cáo (Tích hợp Google Ads, FB Ads)
5. Theo dõi ngân sách quảng cáo (Biểu đồ tiêu tiền thật tế)
6. Thống kê và báo cáo hiệu quả (Xuất file Excel/PDF)
7. Thanh toán và lịch sử giao dịch (Hóa đơn)

## 2. THIẾT KẾ LUỒNG NGHIỆP VỤ (FLOW)
1. Đăng nhập hệ thống (Auth -> Dashboard).
2. Tạo hồ sơ Khách hàng mới.
3. Tạo Chiến dịch quảng cáo gắn với Khách hàng đó.
4. Hệ thống theo dõi click, ngân sách hàng ngày tự động.
5. Cảnh báo (Notification) nếu có bất thường chi phí CPC/Cạn tiền.
6. Kết thúc chiến dịch và in xuất Báo Cáo.

## 3. THIẾT KẾ GIAO DIỆN (UI/UX)
*   **Cấu trúc chung:** Phần mềm Desktop layout, có Navigation Trái (Sidebar trái).
*   **Login form:** Form đăng nhập chia đôi ngang, phối màu xanh Navy / Trắng hiện đại.
*   **Trang Dashboard:** Dashboard dạng thẻ Cards, Stack widget để load trang mà không bị trễ cửa sổ.
*   **Quản lý chiến dịch:** Hiển thị danh sách chiến dịch bằng TableWidget (bảng số liệu), bộ lọc tìm kiếm trên top.
*   **Hiệu ứng (UX):** Hover chuột vào các nút có đổi màu (Hover effect), có cảnh báo nhập thiếu dữ liệu bằng Popup MessageBox.

*(Lưu ý: Đây là tài liệu tóm tắt kết quả phân tích Tuần 1)*
