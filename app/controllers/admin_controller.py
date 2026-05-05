from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, current_app
from app.models import (DBModel, CampaignModel, CustomerModel, InquiryModel,
                        DailyReportModel, NotificationModel, AuditLogModel, CreativeModel, TransactionModel, UserModel, PlatformModel, SpendingModel)
from app.utils.notifications import check_budget_and_notify
from functools import wraps
from datetime import datetime
import os
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Decorators RBAC
# ─────────────────────────────────────────────────────────────────────────────

def require_role_api(roles):
    """Decorator cho API routes — trả JSON 401/403 khi không có quyền."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'success': False, 'message': 'Hết hạn đăng nhập!'}), 401
            if session.get('role') not in roles:
                return jsonify({'success': False, 'message': 'Không có quyền truy cập!'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role_page(roles):
    """Decorator cho Page routes — redirect về login khi không có quyền."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('public.login_page'))
            if session.get('role') not in roles:
                return redirect(url_for('public.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Alias backward compatible
require_role = require_role_api


# ─────────────────────────────────────────────────────────────────────────────
# Page Routes
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@require_role_page(['admin', 'marketer', 'client'])
def dashboard():
    customer_balance = 0
    if session.get('role') == 'client' and session.get('customer_id'):
        cust = CustomerModel.get_by_id(session['customer_id'])
        if cust:
            customer_balance = float(cust.get('balance') or 0)
        return render_template('admin/client_dashboard.html', balance=customer_balance)
    return render_template('admin/dashboard.html')


@admin_bp.route('/campaigns/create')
@require_role_page(['admin', 'marketer', 'client'])
def create_campaign():
    return render_template('admin/create_campaign.html')


@admin_bp.route('/campaigns')
@require_role_page(['admin', 'marketer', 'client'])
def campaigns():
    return render_template('admin/campaigns.html')


# ─────────────────────────────────────────────────────────────────────────────
# API — Stats & Lists
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/stats')
@require_role_api(['admin', 'marketer', 'client'])
def get_stats():
    role    = session['role']
    cust_id = session.get('customer_id')

    if role == 'client' and cust_id:
        res = DBModel.fetch_one(
            "SELECT COUNT(*) as cnt, SUM(budget) as b, SUM(spent) as s "
            "FROM campaigns WHERE customer_id = %s AND is_deleted = 0",
            (cust_id,)
        )
        stats = {
            'total_campaigns': res['cnt'],
            'total_budget':    float(res['b'] or 0),
            'total_spent':     float(res['s'] or 0),
            'total_customers': 1
        }
    elif role == 'marketer':
        user_id = session.get('user_id')
        res = DBModel.fetch_one(
            "SELECT COUNT(c.id) as cnt, SUM(c.budget) as b, SUM(c.spent) as s "
            "FROM campaigns c JOIN customers cu ON c.customer_id = cu.id "
            "WHERE cu.marketer_id = %s AND c.is_deleted = 0",
            (user_id,)
        )
        cust_cnt = DBModel.fetch_one("SELECT COUNT(*) as cnt FROM customers WHERE marketer_id = %s AND is_deleted = 0", (user_id,))['cnt']
        stats = {
            'total_campaigns': res['cnt'],
            'total_budget':    float(res['b'] or 0),
            'total_spent':     float(res['s'] or 0),
            'total_customers': cust_cnt
        }
    else:
        res      = DBModel.fetch_one("SELECT COUNT(*) as cnt, SUM(budget) as b, SUM(spent) as s FROM campaigns WHERE is_deleted = 0")
        cust_cnt = DBModel.fetch_one("SELECT COUNT(*) as cnt FROM customers WHERE is_deleted = 0")['cnt']
        stats = {
            'total_campaigns': res['cnt'],
            'total_budget':    float(res['b'] or 0),
            'total_spent':     float(res['s'] or 0),
            'total_customers': cust_cnt
        }
    return jsonify(stats)


# ─────────────────────────────────────────────────────────────────────────────
# Advanced Dashboard Endpoints (v2)
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/approval-queue')
@require_role_api(['admin', 'marketer'])
def get_approval_queue():
    """Lấy danh sách các mục đang chờ phê duyệt."""
    # 1. Nạp tiền mới
    pending_txs = TransactionModel.get_all(status='pending')
    
    # 2. Chiến dịch mới
    pending_cams = DBModel.fetch_all(
        "SELECT c.*, cu.name as customer_name FROM campaigns c "
        "JOIN customers cu ON c.customer_id = cu.id "
        "WHERE c.approval_status = 'pending' AND c.is_deleted = 0"
    )
    
    # 3. Mẫu quảng cáo cần rà soát
    pending_creatives = DBModel.fetch_all(
        "SELECT cr.*, cam.name as campaign_name FROM creatives cr "
        "JOIN campaigns cam ON cr.campaign_id = cam.id "
        "WHERE cr.status = 'Chờ duyệt'"
    )
    
    return jsonify({
        'transactions': pending_txs,
        'campaigns': pending_cams,
        'creatives': pending_creatives,
        'total_pending': len(pending_txs) + len(pending_cams) + len(pending_creatives)
    })


@admin_bp.route('/api/admin/agency-revenue')
@require_role_api(['admin'])
def get_agency_revenue():
    """Tính toán doanh thu thực thu dựa trên phí dịch vụ (mặc định 10% ngân sách chi tiêu)."""
    # Lấy dữ liệu chi tiêu 6 tháng gần nhất để vẽ biểu đồ
    sql = """
        SELECT DATE_FORMAT(report_date, '%Y-%m') as month, 
               SUM(daily_spent) as total_spent,
               SUM(daily_spent * 0.1) as revenue -- Giả định phí dịch vụ 10%
        FROM daily_reports
        WHERE report_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY month
        ORDER BY month ASC
    """
    data = DBModel.fetch_all(sql)
    return jsonify(data)


@admin_bp.route('/api/admin/staff-performance')
@require_role_api(['admin'])
def get_staff_performance():
    """Hiệu suất nhân sự Marketer."""
    sql = """
        SELECT u.id, u.username, u.full_name,
               COUNT(DISTINCT cu.id) as customer_count,
               COALESCE(SUM(ca.budget), 0) as total_budget_managed,
               COALESCE(SUM(dr.conversions) / NULLIF(SUM(dr.clicks), 0) * 100, 0) as avg_conv_rate
        FROM users u
        LEFT JOIN customers cu ON u.id = cu.marketer_id
        LEFT JOIN campaigns ca ON cu.id = ca.customer_id AND ca.is_deleted = 0
        LEFT JOIN daily_reports dr ON ca.id = dr.campaign_id
        WHERE u.role = 'marketer' AND u.is_active = 1
        GROUP BY u.id
    """
    performance = DBModel.fetch_all(sql)
    return jsonify(performance)


@admin_bp.route('/api/admin/audit-logs')
@require_role_api(['admin'])
def get_audit_logs():
    """Lấy 50 log gần nhất."""
    sql = """
        SELECT a.*, u.username, u.role
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
        LIMIT 50
    """
    logs = DBModel.fetch_all(sql)
    for log in logs:
        if log['created_at']:
            log['created_at'] = log['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(logs)


@admin_bp.route('/api/client/metrics')
@require_role_api(['client'])
def get_client_metrics():
    """Các chỉ số nâng cao cho Client: CPL, Burn Rate."""
    cust_id = session.get('customer_id')
    if not cust_id:
        return jsonify({'error': 'Không tìm thấy thông tin khách hàng'}), 400

    # 1. CPL & Conversions
    sql_metrics = """
        SELECT SUM(daily_spent) as total_spent,
               SUM(conversions) as total_conv,
               SUM(daily_spent) / NULLIF(SUM(conversions), 0) as cpl
        FROM daily_reports dr
        JOIN campaigns c ON dr.campaign_id = c.id
        WHERE c.customer_id = %s AND c.is_deleted = 0
    """
    metrics = DBModel.fetch_one(sql_metrics, (cust_id,))

    # 2. Burn Rate (Dự báo hết tiền)
    # Lấy chi tiêu trung bình 7 ngày qua
    sql_avg_spend = """
        SELECT SUM(daily_spent) / 7 as avg_daily_spend
        FROM daily_reports dr
        JOIN campaigns c ON dr.campaign_id = c.id
        WHERE c.customer_id = %s AND dr.report_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    """
    avg_spend_res = DBModel.fetch_one(sql_avg_spend, (cust_id,))
    avg_daily_spend = float(avg_spend_res['avg_daily_spend'] or 0) if avg_spend_res else 0

    cust = CustomerModel.get_by_id(cust_id)
    balance = float(cust['balance'] or 0)
    
    days_remaining = None
    if avg_daily_spend > 0:
        days_remaining = int(balance / avg_daily_spend)

    return jsonify({
        'total_conversions': int(metrics['total_conv'] or 0),
        'cpl': float(metrics['cpl'] or 0),
        'avg_daily_spend': avg_daily_spend,
        'balance': balance,
        'days_remaining': days_remaining
    })


@admin_bp.route('/api/platforms/status')
@require_role_api(['admin', 'marketer', 'client'])
def get_platform_status():
    """Trạng thái kết nối các nền tảng."""
    return jsonify(PlatformModel.get_all())


@admin_bp.route('/admin-v2')
@require_role_page(['admin'])
def admin_dashboard_v2():
    """Trang Dashboard Admin phiên bản 2."""
    return render_template('admin/admin_dashboard_v2.html')


@admin_bp.route('/api/campaigns')
@require_role_api(['admin', 'marketer', 'client'])
def get_campaigns():
    """Lấy danh sách chiến dịch kèm label hiệu quả."""
    cams   = CampaignModel.get_by_role(session['role'], session.get('customer_id'), session.get('user_id'))
    result = []

    for c in cams:
        budget = float(c.get('budget') or 0)
        spent  = float(c.get('spent')  or 0)
        ratio  = (spent / budget) if budget > 0 else 0

        if ratio < 0.8:
            c['efficiency_label'] = 'Tốt'
            c['efficiency_css']   = 'emerald'
        elif ratio < 0.9:
            c['efficiency_label'] = 'Cần tối ưu'
            c['efficiency_css']   = 'amber'
        else:
            c['efficiency_label'] = 'Cảnh báo'
            c['efficiency_css']   = 'red'

        # Chuyển Decimal sang float để JSON serialize được
        c['budget'] = float(c.get('budget') or 0)
        c['spent']  = float(c.get('spent')  or 0)
        result.append(c)

    return jsonify(result)


@admin_bp.route('/api/customers')
@require_role_api(['admin', 'marketer'])
def get_customers():
    """Danh sách khách hàng cho dropdown form."""
    customers = DBModel.fetch_all("SELECT id, name FROM customers ORDER BY name")
    return jsonify(customers)


# ─────────────────────────────────────────────────────────────────────────────
# API — Campaign CRUD
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/campaigns/add', methods=['POST'])
@require_role_api(['admin', 'marketer', 'client'])
def add_campaign():
    """Thêm chiến dịch mới và nội dung quảng cáo (Creative)."""
    data = request.json or {}

    # Campaign fields
    name        = (data.get('name') or '').strip()
    objective   = (data.get('objective') or '').strip()
    customer_id = data.get('customer_id')
    platform    = (data.get('platform') or '').strip()
    budget      = data.get('budget')
    start_date  = data.get('start_date') or None
    end_date    = data.get('end_date')   or None
    target_link = (data.get('target_link') or '').strip()

    # Creative fields
    creative_title = (data.get('creative_title') or name).strip()
    creative_desc  = (data.get('creative_desc') or '').strip()
    media_url      = (data.get('media_url') or '').strip()
    media_type     = (data.get('media_type') or 'image').strip()

    # ── Validate ─────────────────────────────────────────────────────────
    if not name:
        return jsonify({'success': False, 'message': 'Tên chiến dịch không được để trống!'}), 400
    if not customer_id:
        return jsonify({'success': False, 'message': 'Vui lòng chọn khách hàng!'}), 400
    if not platform:
        return jsonify({'success': False, 'message': 'Vui lòng chọn nền tảng!'}), 400
    try:
        budget = float(budget)
        if budget <= 0:
            return jsonify({'success': False, 'message': 'Ngân sách phải là số dương!'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Ngân sách không hợp lệ!'}), 400

    if start_date and end_date:
        try:
            if datetime.strptime(start_date, '%Y-%m-%d') >= datetime.strptime(end_date, '%Y-%m-%d'):
                return jsonify({'success': False, 'message': 'Ngày bắt đầu phải trước ngày kết thúc!'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Định dạng ngày không hợp lệ!'}), 400

    try:
        # 1. Tạo Campaign
        new_id = CampaignModel.create(name, customer_id, platform, budget, start_date, end_date, target_link, objective)
        
        # 2. Tạo Creative mặc định đi kèm
        CreativeModel.create(new_id, creative_title, media_type, media_url, creative_desc)

        # Ghi log
        AuditLogModel.log(session['user_id'], 'CREATE_CAMPAIGN_FULL', 'campaigns', new_id, None, 
                          {'name': name, 'objective': objective, 'customer_id': customer_id, 'platform': platform, 'budget': budget})
        
        return jsonify({'success': True, 'message': f'Đã tạo chiến dịch và nội dung quảng cáo thành công!', 'id': new_id})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@admin_bp.route('/api/campaigns/<int:campaign_id>/update', methods=['PUT'])
@require_role_api(['admin', 'marketer'])
def update_campaign(campaign_id):
    """Cập nhật thông tin chiến dịch."""
    data = request.json or {}

    name        = (data.get('name') or '').strip()
    platform    = (data.get('platform') or '').strip()
    target_link = (data.get('target_link') or '').strip()
    status      = data.get('status', 'Đang chạy')
    start_date  = data.get('start_date') or None
    end_date    = data.get('end_date')   or None

    if not name:
        return jsonify({'success': False, 'message': 'Tên chiến dịch không được để trống!'}), 400

    try:
        budget = float(data.get('budget', 0))
        spent  = float(data.get('spent',  0))
        if budget <= 0:
            return jsonify({'success': False, 'message': 'Ngân sách phải là số dương!'}), 400
        if spent < 0:
            return jsonify({'success': False, 'message': 'Chi phí không được âm!'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Ngân sách hoặc chi phí không hợp lệ!'}), 400

    if start_date and end_date:
        try:
            if datetime.strptime(start_date, '%Y-%m-%d') >= datetime.strptime(end_date, '%Y-%m-%d'):
                return jsonify({'success': False, 'message': 'Ngày bắt đầu phải trước ngày kết thúc!'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Định dạng ngày không hợp lệ!'}), 400

    try:
        old_val = CampaignModel.get_by_id(campaign_id)
        if not old_val:
            return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404

        # Check permission for marketer
        if session.get('role') == 'marketer':
            cust = CustomerModel.get_by_id(old_val['customer_id'])
            if not cust or cust.get('marketer_id') != session.get('user_id'):
                return jsonify({'success': False, 'message': 'Không có quyền chỉnh sửa chiến dịch này!'}), 403

        CampaignModel.update(campaign_id, name, platform, target_link, budget, spent, status, start_date, end_date)
        
        # Ghi log
        AuditLogModel.log(session['user_id'], 'UPDATE_CAMPAIGN', 'campaigns', campaign_id, old_val, 
                          {'name': name, 'platform': platform, 'budget': budget, 'status': status})
        
        return jsonify({'success': True, 'message': f'Đã cập nhật chiến dịch "{name}" thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@admin_bp.route('/api/campaigns/<int:campaign_id>/delete', methods=['DELETE'])
@require_role_api(['admin'])
def delete_campaign(campaign_id):
    """Xóa chiến dịch. Chỉ Admin."""
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404
    try:
        CampaignModel.delete(campaign_id)
        return jsonify({'success': True, 'message': f'Đã xóa chiến dịch "{cam["name"]}" thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@admin_bp.route('/api/campaigns/<int:campaign_id>/efficiency')
@require_role_api(['admin', 'marketer', 'client'])
def campaign_efficiency(campaign_id):
    """Chỉ số hiệu quả của một chiến dịch."""
    stats = CampaignModel.get_efficiency_stats(campaign_id)
    if not stats:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404
    return jsonify({'success': True, 'data': stats})


# ─────────────────────────────────────────────────────────────────────────────
# Page Routes — Customers
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/customers')
@require_role_page(['admin', 'marketer'])
def customers():
    return render_template('admin/customers.html')


@admin_bp.route('/users')
@require_role_page(['admin'])
def users_page():
    """Trang quản lý người dùng hệ thống."""
    return render_template('admin/users.html')


@admin_bp.route('/api/users')
@require_role_api(['admin'])
def get_users():
    """Lấy danh sách user kèm thông tin khách hàng liên kết."""
    users = UserModel.get_all()
    # Chuyển đổi created_at sang string
    for u in users:
        if u['created_at']:
            u['created_at'] = u['created_at'].strftime('%Y-%m-%d %H:%M')
    return jsonify(users)


@admin_bp.route('/api/users/add', methods=['POST'])
@require_role_api(['admin'])
def add_user():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    role        = data.get('role', 'marketer')
    customer_id = data.get('customer_id')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Thiếu tên đăng nhập hoặc mật khẩu!'}), 400
        
    if UserModel.get_by_username(username):
        return jsonify({'success': False, 'message': 'Tên đăng nhập đã tồn tại!'}), 400
        
    try:
        UserModel.create(username, password, role, customer_id)
        return jsonify({'success': True, 'message': f'Đã tạo tài khoản "{username}" thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/users/<int:user_id>/update', methods=['PUT'])
@require_role_api(['admin'])
def update_user(user_id):
    data     = request.json or {}
    role     = data.get('role')
    password = data.get('password') # Optional
    
    try:
        UserModel.update(user_id, role=role, password=password, customer_id=data.get('customer_id'))
        return jsonify({'success': True, 'message': 'Cập nhật thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/users/<int:user_id>/toggle-status', methods=['PUT'])
@require_role_api(['admin'])
def toggle_user_status(user_id):
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'message': 'Bạn không thể tự khóa tài khoản của chính mình!'}), 400
    try:
        UserModel.toggle_active(user_id)
        return jsonify({'success': True, 'message': 'Đã thay đổi trạng thái tài khoản!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─── Quản lý Nền tảng (Dịch vụ) ──────────────────────────────────────────

@admin_bp.route('/platforms')
@require_role_page(['admin'])
def platforms_page():
    return render_template('admin/platforms.html')


@admin_bp.route('/api/platforms')
@require_role_api(['admin', 'marketer'])
def get_platforms():
    return jsonify(PlatformModel.get_all())


@admin_bp.route('/api/platforms/add', methods=['POST'])
@require_role_api(['admin'])
def add_platform():
    data = request.json or {}
    name = data.get('name')
    acc  = data.get('account_id')
    
    if not name: return jsonify({'success': False, 'message': 'Tên nền tảng không được để trống!'}), 400
    
    try:
        PlatformModel.create(name, acc)
        return jsonify({'success': True, 'message': 'Đã thêm dịch vụ mới!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/platforms/<int:pid>/update', methods=['PUT'])
@require_role_api(['admin'])
def update_platform(pid):
    data   = request.json or {}
    name   = data.get('name')
    acc    = data.get('account_id')
    status = data.get('status')
    
    try:
        PlatformModel.update(pid, name, acc, status)
        return jsonify({'success': True, 'message': 'Cập nhật thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/platforms/<int:pid>/delete', methods=['DELETE'])
@require_role_api(['admin'])
def delete_platform(pid):
    try:
        PlatformModel.delete(pid)
        return jsonify({'success': True, 'message': 'Đã xóa dịch vụ!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─── Cập nhật báo cáo chi tiêu (Marketer) ────────────────────────────────

@admin_bp.route('/log-spending')
@require_role_page(['admin', 'marketer'])
def log_spending_page():
    """Trang cập nhật báo cáo chi tiêu hàng ngày."""
    return render_template('admin/log_spending.html')


@admin_bp.route('/api/log-spending', methods=['POST'])
@require_role_api(['admin', 'marketer'])
def log_spending_api():
    """API lưu chi phí hàng ngày và cập nhật tổng chi tiêu chiến dịch."""
    data      = request.json or {}
    cam_id    = data.get('campaign_id')
    date      = data.get('date')
    spent     = float(data.get('spent') or 0)
    clicks    = int(data.get('clicks') or 0)
    impr      = int(data.get('impressions') or 0)

    if not cam_id or not date:
        return jsonify({'success': False, 'message': 'Thiếu thông tin chiến dịch hoặc ngày!'}), 400

    try:
        # 1. Lưu vào daily_spending
        SpendingModel.log_daily_spending(cam_id, date, spent, clicks, impr)
        
        # 2. Đồng bộ tổng chi tiêu vào bảng campaigns.spent
        total_spent = SpendingModel.get_total_spent(cam_id)
        CampaignModel.update_spent(cam_id, total_spent)
        
        # 3. Kiểm tra ngân sách để gửi cảnh báo nếu cần
        check_budget_and_notify(cam_id)
        
        return jsonify({'success': True, 'message': 'Đã cập nhật báo cáo thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



@admin_bp.route('/api/customers/<int:customer_id>/campaigns')
@require_role_api(['admin', 'marketer'])
def get_customer_campaigns(customer_id):
    """Lấy danh sách chiến dịch của 1 khách hàng."""
    try:
        campaigns = CampaignModel.get_by_customer(customer_id)
        # Thêm hiệu quả
        for c in campaigns:
            eff = CampaignModel.get_efficiency_stats(c['id'])
            if eff:
                c['efficiency_label'] = eff['label']
                c['efficiency_css']   = eff['label_css']
        return jsonify(campaigns)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API — Customer CRUD
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/customers/list')
@require_role_api(['admin', 'marketer'])
def get_customers_list():
    """Danh sách đầy đủ khách hàng kèm thống kê chiến dịch."""
    marketer_id = session['user_id'] if session['role'] == 'marketer' else None
    customers = CustomerModel.get_all(marketer_id)
    return jsonify(customers)


@admin_bp.route('/api/customers/add', methods=['POST'])
@require_role_api(['admin', 'marketer'])
def add_customer():
    """Thêm khách hàng mới."""
    data    = request.json or {}
    name    = (data.get('name') or '').strip()
    email   = (data.get('email') or '').strip() or None
    phone   = (data.get('phone') or '').strip() or None
    company = (data.get('company') or '').strip() or None
    marketer_id = data.get('marketer_id')

    if not name:
        return jsonify({'success': False, 'message': 'Tên khách hàng không được để trống!'}), 400
    if email and '@' not in email:
        return jsonify({'success': False, 'message': 'Email không hợp lệ!'}), 400
    if phone and not phone.replace(' ', '').replace('-', '').replace('+', '').isdigit():
        return jsonify({'success': False, 'message': 'Số điện thoại chỉ được chứa chữ số!'}), 400

    try:
        new_id = CustomerModel.create(name, email, phone, company, marketer_id=marketer_id)
        
        # Ghi log
        AuditLogModel.log(session['user_id'], 'CREATE_CUSTOMER', 'customers', new_id, None, 
                          {'name': name, 'email': email, 'company': company, 'marketer_id': marketer_id})
        
        return jsonify({'success': True, 'message': f'Đã thêm khách hàng "{name}"!', 'id': new_id})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@admin_bp.route('/api/customers/<int:customer_id>/update', methods=['PUT'])
@require_role_api(['admin', 'marketer'])
def update_customer(customer_id):
    """Cập nhật thông tin khách hàng."""
    data    = request.json or {}
    name    = (data.get('name') or '').strip()
    email   = (data.get('email') or '').strip() or None
    phone   = (data.get('phone') or '').strip() or None
    company = (data.get('company') or '').strip() or None
    status  = data.get('status', 'Active')
    marketer_id = data.get('marketer_id')

    # Nếu không phải admin thì không được phép đổi marketer_id
    if session['role'] != 'admin':
        old_val = CustomerModel.get_by_id(customer_id)
        if old_val:
            marketer_id = old_val.get('marketer_id')

    if not name:
        return jsonify({'success': False, 'message': 'Tên khách hàng không được để trống!'}), 400

    try:
        old_val = CustomerModel.get_by_id(customer_id)
        CustomerModel.update(customer_id, name, email, phone, company, status, marketer_id=marketer_id)
        
        # Ghi log
        AuditLogModel.log(session['user_id'], 'UPDATE_CUSTOMER', 'customers', customer_id, old_val, 
                          {'name': name, 'email': email, 'company': company, 'status': status, 'marketer_id': marketer_id})
        
        return jsonify({'success': True, 'message': f'Đã cập nhật khách hàng "{name}" thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@admin_bp.route('/api/customers/<int:customer_id>/delete', methods=['DELETE'])
@require_role_api(['admin'])
def delete_customer(customer_id):
    """Xóa khách hàng. Chỉ Admin. Sẽ xóa cascade các campaigns liên quan."""
    cust = CustomerModel.get_by_id(customer_id)
    if not cust:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng!'}), 404
    try:
        CustomerModel.delete(customer_id)
        return jsonify({'success': True, 'message': f'Đã xóa khách hàng "{cust["name"]}" và toàn bộ chiến dịch liên quan!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@admin_bp.route('/api/marketers')
@require_role_api(['admin'])
def get_marketers():
    """Danh sách marketer để phân công khách hàng."""
    marketers = DBModel.fetch_all("SELECT id, username, full_name FROM users WHERE role = 'marketer' AND is_active = 1")
    return jsonify(marketers)


@admin_bp.route('/api/deposit', methods=['POST'])
@require_role_api(['client'])
def deposit():
    """API nạp tiền có bằng chứng chuyển khoản."""
    amount = request.form.get('amount')
    method = request.form.get('method', 'bank')
    file   = request.files.get('proof_image')

    if not amount or float(amount) <= 0:
        return jsonify({'success': False, 'message': 'Số tiền nạp không hợp lệ!'}), 400
    
    if not file:
        return jsonify({'success': False, 'message': 'Vui lòng upload ảnh bằng chứng chuyển khoản!'}), 400

    try:
        # Lưu ảnh
        filename = secure_filename(f"proof_{session['user_id']}_{int(datetime.now().timestamp())}_{file.filename}")
        upload_path = os.path.join('app/static/uploads/proofs')
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        
        file.save(os.path.join(upload_path, filename))
        proof_url = f"/static/uploads/proofs/{filename}"

        # Tạo giao dịch ở trạng thái pending
        TransactionModel.create_transaction(
            customer_id=session['customer_id'],
            t_type='topup',
            amount=float(amount),
            description=f"Nạp tiền qua {method}",
            payment_method=method,
            proof_image=proof_url,
            status='pending'
        )

        AuditLogModel.log(session['user_id'], 'DEPOSIT_REQUEST', 'transactions', None, 
                          None, {'amount': amount, 'method': method})
        
        return jsonify({'success': True, 'message': 'Yêu cầu nạp tiền đã được gửi! Vui lòng chờ Admin phê duyệt.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/transactions')
@require_role_page(['admin'])
def transaction_manage():
    """Trang quản lý nạp tiền (Admin)."""
    return render_template('admin/transaction_manage.html')


@admin_bp.route('/api/transactions')
@require_role_api(['admin'])
def get_transactions():
    """API lấy danh sách giao dịch lọc theo status."""
    status = request.args.get('status')
    txs = TransactionModel.get_all(status=status)
    return jsonify(txs)


@admin_bp.route('/api/transactions/<int:tx_id>/approve', methods=['POST'])
@require_role_api(['admin'])
def approve_transaction(tx_id):
    """Phê duyệt giao dịch nạp tiền."""
    tx = TransactionModel.get_by_id(tx_id)
    if not tx or tx['status'] != 'pending':
        return jsonify({'success': False, 'message': 'Giao dịch không hợp lệ hoặc đã xử lý!'}), 400
    
    try:
        # 1. Cập nhật số dư khách hàng
        CustomerModel.deposit(tx['customer_id'], tx['amount'])
        
        # 2. Cập nhật trạng thái giao dịch
        TransactionModel.update_status(tx_id, 'completed')
        
        # 3. Tạo thông báo cho khách hàng
        user = DBModel.fetch_one("SELECT id FROM users WHERE customer_id = %s", (tx['customer_id'],))
        if user:
            NotificationModel.create(user['id'], "Nạp tiền thành công", 
                                     f"Yêu cầu nạp {tx['amount']:,.0f} VNĐ của bạn đã được phê duyệt.", "success")
        
        AuditLogModel.log(session['user_id'], 'APPROVE_DEPOSIT', 'transactions', tx_id, None, {'amount': tx['amount']})
        
        return jsonify({'success': True, 'message': 'Đã phê duyệt và cộng tiền thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/transactions/<int:tx_id>/reject', methods=['POST'])
@require_role_api(['admin'])
def reject_transaction(tx_id):
    """Từ chối giao dịch nạp tiền."""
    data   = request.json or {}
    reason = data.get('reason', 'Không rõ lý do')
    
    tx = TransactionModel.get_by_id(tx_id)
    if not tx or tx['status'] != 'pending':
        return jsonify({'success': False, 'message': 'Giao dịch không hợp lệ hoặc đã xử lý!'}), 400
    
    try:
        TransactionModel.update_status(tx_id, 'rejected', reason)
        
        user = DBModel.fetch_one("SELECT id FROM users WHERE customer_id = %s", (tx['customer_id'],))
        if user:
            NotificationModel.create(user['id'], "Yêu cầu nạp tiền bị từ chối", 
                                     f"Yêu cầu nạp {tx['amount']:,.0f} VNĐ bị từ chối. Lý do: {reason}", "error")
            
        AuditLogModel.log(session['user_id'], 'REJECT_DEPOSIT', 'transactions', tx_id, None, {'reason': reason})
        
        return jsonify({'success': True, 'message': 'Đã từ chối giao dịch.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API — Inquiry Management
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/inquiries')
@require_role_api(['admin', 'marketer'])
def get_inquiries():
    """Toàn bộ danh sách yêu cầu tư vấn."""
    inquiries = InquiryModel.get_all()
    return jsonify(inquiries)


@admin_bp.route('/api/inquiries/<int:inquiry_id>/approve', methods=['POST'])
@require_role_api(['admin', 'marketer'])
def approve_inquiry(inquiry_id):
    """Phê duyệt inquiry → tạo Customer chính thức."""
    try:
        customer_id = InquiryModel.approve(inquiry_id)
        if customer_id:
            return jsonify({'success': True,
                           'message': 'Đã chuyển đổi thành khách hàng thành công!',
                           'customer_id': customer_id})
        return jsonify({'success': False, 'message': 'Không tìm thấy yêu cầu tư vấn!'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@admin_bp.route('/api/inquiries/<int:inquiry_id>/read', methods=['POST'])
@require_role_api(['admin', 'marketer'])
def mark_inquiry_read(inquiry_id):
    """Đánh dấu yêu cầu đã đọc."""
    InquiryModel.mark_read(inquiry_id)
    return jsonify({'success': True})


# ─────────────────────────────────────────────────────────────────────────────
# API — Daily Report & Budget Alert (Module 3)
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/campaigns/<int:campaign_id>/log-daily', methods=['POST'])
@require_role_api(['admin', 'marketer'])
def log_daily(campaign_id):
    """
    Ghi nhận chi phí trong ngày cho chiến dịch.
    Body JSON: { daily_spent, clicks, impressions, conversions, report_date (optional) }
    Logic tự động:
      - spent > 90% budget  → tạo notification 'budget_warning'
      - spent >= 100% budget → đổi status='Tạm dừng', tạo notification 'budget_exceeded'
    """
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404

    data = request.json or {}

    try:
        daily_spent  = float(data.get('daily_spent', 0))
        clicks       = int(data.get('clicks', 0))
        impressions  = int(data.get('impressions', 0))
        conversions  = int(data.get('conversions', 0))
        if daily_spent < 0:
            return jsonify({'success': False, 'message': 'Chi phí không được âm!'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ!'}), 400

    report_date = data.get('report_date') or datetime.today().strftime('%Y-%m-%d')

    # Ghi nhận vào daily_reports (upsert)
    DailyReportModel.log_daily(campaign_id, report_date, daily_spent, clicks, impressions, conversions)

    # Cộng dồn vào cột spent của campaigns
    new_spent = float(cam['spent'] or 0) + daily_spent
    budget    = float(cam['budget'] or 1)
    ratio     = new_spent / budget

    # Cập nhật spent
    DBModel.execute(
        "UPDATE campaigns SET spent = %s WHERE id = %s",
        (new_spent, campaign_id)
    )

    notification_msg = None
    # Kiểm tra ngưỡng cảnh báo
    if ratio >= 1.0:
        # Vượt ngân sách → tạm dừng chiến dịch
        DBModel.execute(
            "UPDATE campaigns SET status = 'Tạm dừng' WHERE id = %s AND status != 'Tạm dừng'",
            (campaign_id,)
        )
        msg = (f"Chiến dịch \"{cam['name']}\" đã vượt ngân sách "
               f"({new_spent:,.0f} / {budget:,.0f} VND). Tự động tạm dừng!")
        NotificationModel.create(campaign_id, NotificationModel.TYPE_BUDGET_EXCEEDED, msg)
        notification_msg = msg
    elif ratio >= 0.9:
        # Cảnh báo ngưỡng 90%
        msg = (f"Chiến dịch \"{cam['name']}\" đã dùng {ratio*100:.1f}% ngân sách "
               f"({new_spent:,.0f} / {budget:,.0f} VND). Cần theo dõi!")
        # Chỉ tạo 1 thông báo mỗi ngày (kiểm tra trùng theo ngày)
        existing = DBModel.fetch_one(
            "SELECT id FROM notifications WHERE campaign_id=%s AND type=%s AND DATE(created_at)=CURDATE()",
            (campaign_id, NotificationModel.TYPE_BUDGET_WARNING)
        )
        if not existing:
            NotificationModel.create(campaign_id, NotificationModel.TYPE_BUDGET_WARNING, msg)
            notification_msg = msg
            # Gửi cảnh báo Telegram
            check_budget_and_notify(cam, new_spent)

    response = {
        'success': True,
        'message': f'Đã ghi nhận chi phí {daily_spent:,.0f} VND!',
        'new_spent': new_spent,
        'ratio': round(ratio, 4),
        'status': 'exceeded' if ratio >= 1.0 else ('warning' if ratio >= 0.9 else 'ok'),
    }
    if notification_msg:
        response['alert'] = notification_msg

    return jsonify(response)



# ─────────────────────────────────────────────────────────────────────────────
# API — Dashboard & Analytics Charts (Module 4)
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/chart/spending-trend')
@require_role_api(['admin', 'marketer', 'client'])
def chart_spending_trend():
    """Chi phí 7 ngày gần nhất từ bảng daily_reports."""
    role    = session['role']
    cust_id = session.get('customer_id')

    if role == 'client' and cust_id:
        sql = """
            SELECT dr.date as report_date, SUM(dr.amount_spent) AS total_spent
            FROM   daily_spending dr
            JOIN   campaigns c ON dr.campaign_id = c.id
            WHERE  c.customer_id = %s AND c.is_deleted = 0
              AND  dr.date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY dr.date
            ORDER BY dr.date ASC
        """
        rows = DBModel.fetch_all(sql, (cust_id,))
    elif role == 'marketer':
        user_id = session.get('user_id')
        sql = """
            SELECT dr.date as report_date, SUM(dr.amount_spent) AS total_spent
            FROM   daily_spending dr
            JOIN   campaigns c ON dr.campaign_id = c.id
            JOIN   customers cu ON c.customer_id = cu.id
            WHERE  cu.marketer_id = %s AND c.is_deleted = 0
              AND  dr.date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY dr.date
            ORDER BY dr.date ASC
        """
        rows = DBModel.fetch_all(sql, (user_id,))
    else:
        sql = """
            SELECT dr.date as report_date, SUM(dr.amount_spent) AS total_spent
            FROM   daily_spending dr
            JOIN   campaigns c ON dr.campaign_id = c.id
            WHERE  c.is_deleted = 0
              AND  dr.date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY dr.date
            ORDER BY dr.date ASC
        """
        rows = DBModel.fetch_all(sql)

    labels = [r['report_date'].strftime('%d/%m') if hasattr(r['report_date'], 'strftime') else str(r['report_date']) for r in rows]
    data   = [float(r['total_spent'] or 0) for r in rows]
    return jsonify({'labels': labels, 'data': data})


@admin_bp.route('/api/chart/platform-distribution')
@require_role_api(['admin', 'marketer', 'client'])
def chart_platform_distribution():
    """Phân bổ ngân sách (budget) theo nền tảng, lọc theo role."""
    role    = session['role']
    cust_id = session.get('customer_id')

    if role == 'client' and cust_id:
        sql = """
            SELECT platform, SUM(budget) AS total
            FROM   campaigns
            WHERE  customer_id = %s AND is_deleted = 0
            GROUP BY platform ORDER BY total DESC
        """
        rows = DBModel.fetch_all(sql, (cust_id,))
    elif role == 'marketer':
        user_id = session.get('user_id')
        sql = """
            SELECT c.platform, SUM(c.budget) AS total
            FROM   campaigns c
            JOIN   customers cu ON c.customer_id = cu.id
            WHERE  cu.marketer_id = %s AND c.is_deleted = 0
            GROUP BY c.platform ORDER BY total DESC
        """
        rows = DBModel.fetch_all(sql, (user_id,))
    else:
        sql = "SELECT platform, SUM(budget) AS total FROM campaigns WHERE is_deleted = 0 GROUP BY platform ORDER BY total DESC"
        rows = DBModel.fetch_all(sql)

    labels = [r['platform'] for r in rows]
    data   = [float(r['total'] or 0) for r in rows]
    return jsonify({'labels': labels, 'data': data})


@admin_bp.route('/api/chart/campaign-status')
@require_role_api(['admin', 'marketer', 'client'])
def chart_campaign_status():
    """Số lượng chiến dịch theo trạng thái."""
    role    = session['role']
    cust_id = session.get('customer_id')

    if role == 'client' and cust_id:
        sql = "SELECT status, COUNT(*) AS cnt FROM campaigns WHERE customer_id=%s AND is_deleted = 0 GROUP BY status"
        rows = DBModel.fetch_all(sql, (cust_id,))
    elif role == 'marketer':
        user_id = session.get('user_id')
        sql = """
            SELECT c.status, COUNT(*) AS cnt 
            FROM campaigns c 
            JOIN customers cu ON c.customer_id = cu.id 
            WHERE cu.marketer_id=%s AND c.is_deleted = 0 
            GROUP BY c.status
        """
        rows = DBModel.fetch_all(sql, (user_id,))
    else:
        sql = "SELECT status, COUNT(*) AS cnt FROM campaigns WHERE is_deleted = 0 GROUP BY status"
        rows = DBModel.fetch_all(sql)

    labels = [r['status'] for r in rows]
    data   = [int(r['cnt']) for r in rows]
    return jsonify({'labels': labels, 'data': data})


@admin_bp.route('/api/top-campaigns')
@require_role_api(['admin', 'marketer', 'client'])
def top_campaigns():
    """Top 5 chiến dịch chi phí cao nhất 30 ngày gần đây."""
    role    = session['role']
    cust_id = session.get('customer_id')

    base_sql = """
        SELECT c.id, c.name, c.platform, c.budget, c.spent, c.status,
               cu.name AS customer_name,
               ROUND(c.spent / NULLIF(c.budget, 0) * 100, 1) AS spent_ratio
        FROM   campaigns c
        LEFT JOIN customers cu ON c.customer_id = cu.id
        {where}
        ORDER BY c.spent DESC
        LIMIT 5
    """
    if role == 'client' and cust_id:
        sql  = base_sql.format(where="WHERE c.customer_id = %s AND c.is_deleted = 0")
        rows = DBModel.fetch_all(sql, (cust_id,))
    elif role == 'marketer':
        user_id = session.get('user_id')
        sql  = base_sql.format(where="WHERE cu.marketer_id = %s AND c.is_deleted = 0")
        rows = DBModel.fetch_all(sql, (user_id,))
    else:
        sql  = base_sql.format(where="WHERE c.is_deleted = 0")
        rows = DBModel.fetch_all(sql)

    result = []
    for r in rows:
        result.append({
            'id':            r['id'],
            'name':          r['name'],
            'platform':      r['platform'],
            'budget':        float(r['budget'] or 0),
            'spent':         float(r['spent'] or 0),
            'spent_ratio':   float(r['spent_ratio'] or 0),
            'status':        r['status'],
            'customer_name': r['customer_name'] or '—',
        })
    return jsonify(result)


# ─────────────────────────────────────────────────────────────────────────────
# Page Routes — Reports & Dashboard (Module 4 & 5)
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/reports')
@require_role_page(['admin', 'marketer'])
def reports():
    return render_template('admin/reports.html')


@admin_bp.route('/deposit')
@require_role_page(['admin', 'marketer', 'client'])
def deposit_page():
    customer_balance = 0
    if session.get('customer_id'):
        cust = CustomerModel.get_by_id(session['customer_id'])
        if cust:
            customer_balance = float(cust.get('balance') or 0)
    return render_template('admin/deposit.html', balance=customer_balance)


@admin_bp.route('/campaigns/<int:campaign_id>')
@require_role_page(['admin', 'marketer', 'client'])
def campaign_detail(campaign_id):
    """Trang chi tiết của 1 chiến dịch và duyệt mẫu quảng cáo."""
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return "Campaign not found", 404
        
    role    = session.get('role')
    user_id = session.get('user_id')

    # Check permission for client
    if role == 'client' and cam['customer_id'] != session.get('customer_id'):
        return "Unauthorized", 403
    
    # Check permission for marketer
    if role == 'marketer':
        cust = CustomerModel.get_by_id(cam['customer_id'])
        if not cust or cust.get('marketer_id') != user_id:
            return "Unauthorized", 403

    creatives = CreativeModel.get_by_campaign(campaign_id)
    return render_template('admin/campaign_detail.html', campaign=cam, creatives=creatives)


# ─────────────────────────────────────────────────────────────────────────────
# API — Creatives (Approval Workflow)
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/campaigns/<int:campaign_id>/creatives', methods=['POST'])
@require_role_api(['admin', 'marketer'])
def add_creative(campaign_id):
    """Marketer thêm mẫu quảng cáo mới vào chiến dịch để khách hàng duyệt."""
    data = request.json or {}
    name       = (data.get('name') or '').strip()
    media_type = data.get('media_type', 'image')
    media_url  = (data.get('media_url') or '').strip()
    content    = (data.get('content') or '').strip()

    if not name or not media_url:
        return jsonify({'success': False, 'message': 'Vui lòng nhập tên và link mẫu quảng cáo!'}), 400

    try:
        CreativeModel.create(campaign_id, name, media_type, media_url, content)
        AuditLogModel.log(session['user_id'], 'ADD_CREATIVE', 'campaigns', campaign_id, None, data)
        return jsonify({'success': True, 'message': 'Đã gửi mẫu quảng cáo cho khách hàng!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/creatives/<int:creative_id>/approve', methods=['PUT'])
@require_role_api(['client', 'admin', 'marketer'])
def approve_creative(creative_id):
    """Đổi trạng thái mẫu quảng cáo sang Đã duyệt."""
    try:
        CreativeModel.update_status(creative_id, 'Đã duyệt', '')
        AuditLogModel.log(session['user_id'], 'APPROVE_CREATIVE', 'creatives', creative_id, None, {})
        return jsonify({'success': True, 'message': 'Đã duyệt mẫu quảng cáo!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/creatives/<int:creative_id>/reject', methods=['PUT'])
@require_role_api(['client', 'admin', 'marketer'])
def reject_creative(creative_id):
    """Từ chối mẫu quảng cáo kèm lý do."""
    data = request.json or {}
    feedback = (data.get('feedback') or '').strip()
    
    if not feedback:
        return jsonify({'success': False, 'message': 'Vui lòng cung cấp lý do từ chối!'}), 400
        
    try:
        CreativeModel.update_status(creative_id, 'Từ chối', feedback)
        AuditLogModel.log(session['user_id'], 'REJECT_CREATIVE', 'creatives', creative_id, None, {'feedback': feedback})
        return jsonify({'success': True, 'message': 'Đã từ chối mẫu quảng cáo!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API — Campaign Workflow
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/campaigns/<int:campaign_id>/approve', methods=['PUT'])
@require_role_api(['admin', 'client'])
def approve_campaign(campaign_id):
    """Admin hoặc Khách hàng duyệt chiến dịch để bắt đầu chạy."""
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404
        
    try:
        # Cập nhật cả approval_status (cho logic cũ) và status (cho UI mới)
        DBModel.execute("UPDATE campaigns SET approval_status = 'active', status = 'Đang chạy' WHERE id = %s", (campaign_id,))
        AuditLogModel.log(session['user_id'], 'APPROVE_CAMPAIGN', 'campaigns', campaign_id, cam.get('approval_status'), 'active')
        return jsonify({'success': True, 'message': 'Chiến dịch đã được duyệt thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/campaigns/<int:campaign_id>/reject', methods=['PUT'])
@require_role_api(['admin'])
def reject_campaign(campaign_id):
    """Admin từ chối chiến dịch."""
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404
        
    try:
        DBModel.execute("UPDATE campaigns SET approval_status = 'paused', status = 'Từ chối' WHERE id = %s", (campaign_id,))
        AuditLogModel.log(session['user_id'], 'REJECT_CAMPAIGN', 'campaigns', campaign_id, cam.get('approval_status'), 'paused')
        return jsonify({'success': True, 'message': 'Đã từ chối chiến dịch!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API — Notifications
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/notifications')
@require_role_api(['admin', 'marketer', 'client'])
def get_notifications():
    """Lấy danh sách thông báo chưa đọc của user hiện tại."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'data': [], 'unread_count': 0})
        
    try:
        from app.models.notification import NotificationModel
        items = NotificationModel.get_unread(user_id)
        count = NotificationModel.get_unread_count(user_id)
        return jsonify({'data': items, 'unread_count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@require_role_api(['admin', 'marketer', 'client'])
def mark_notification_read(notif_id):
    """Đánh dấu 1 thông báo là đã đọc."""
    user_id = session.get('user_id')
    try:
        from app.models.notification import NotificationModel
        NotificationModel.mark_read(notif_id, user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/notifications/read-all', methods=['POST'])
@require_role_api(['admin', 'marketer', 'client'])
def mark_all_notifications_read():
    """Đánh dấu tất cả thông báo của user là đã đọc."""
    user_id = session.get('user_id')
    try:
        from app.models.notification import NotificationModel
        NotificationModel.mark_all_read(user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/ad/preview/<int:campaign_id>')
@require_role_page(['admin', 'marketer', 'client'])
def ad_preview(campaign_id):
    """Trang xem trước Mockup quảng cáo trên mobile."""
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return redirect(url_for('admin.campaigns'))
        
    role = session.get('role')
    if role == 'client' and cam['customer_id'] != session.get('customer_id'):
        return redirect(url_for('admin.dashboard'))

    creatives = CreativeModel.get_by_campaign(campaign_id)
    # Lấy creative đã duyệt, nếu không có thì lấy cái mới nhất
    creative = next((c for c in creatives if c['status'] == 'Đã duyệt'), None)
    if not creative and creatives:
        creative = creatives[0]

    return render_template('admin/ad_preview.html', campaign=cam, creative=creative)


@admin_bp.route('/customers/<int:customer_id>')
@require_role_page(['admin', 'marketer'])
def customer_detail(customer_id):
    """Trang thông tin chi tiết khách hàng (sử dụng trang danh sách kèm filter)."""
    return redirect(url_for('admin.customers', id=customer_id))
