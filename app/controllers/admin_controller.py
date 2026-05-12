from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, current_app
from app.models import (DBModel, CampaignModel, CustomerModel, InquiryModel,
                        DailyReportModel, NotificationModel, AuditLogModel, CreativeModel, TransactionModel, UserModel, PlatformModel, SpendingModel, CampaignPlatformModel)
from app.utils.notifications import check_budget_and_notify
from functools import wraps
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from app.extensions import db, limiter
from app.utils.validation import validate_schema, CampaignCreateSchema
from decimal import Decimal

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
            
            # KIỂM TRA TRẠNG THÁI TÀI KHOẢN (Security Guard)
            user = UserModel.get_by_id(session['user_id'])
            if not user or not user.is_active:
                session.clear()
                return redirect(url_for('public.login_page', error='Tài khoản của bạn đã bị tạm khóa'))
                
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
            customer_balance = float(cust.balance or 0)
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
@require_role_api(['admin', 'marketer', 'client'])
def get_approval_queue():
    """Lấy danh sách các mục đang chờ phê duyệt (đã lọc theo quyền)."""
    role    = session['role']
    cust_id = session.get('customer_id')
    user_id = session.get('user_id')

    pending_txs = []
    if role == 'admin':
        pending_txs = TransactionModel.get_all(status='pending')
    
    # 2. Chiến dịch mới
    if role == 'admin':
        pending_cams = DBModel.fetch_all(
            "SELECT c.*, cu.name as customer_name FROM campaigns c "
            "JOIN customers cu ON c.customer_id = cu.id "
            "WHERE c.approval_status = 'pending' AND c.is_deleted = 0"
        )
    elif role == 'marketer':
        pending_cams = DBModel.fetch_all(
            "SELECT c.*, cu.name as customer_name FROM campaigns c "
            "JOIN customers cu ON c.customer_id = cu.id "
            "WHERE c.approval_status = 'pending' AND c.is_deleted = 0 AND cu.marketer_id = %s",
            (user_id,)
        )
    else: # client
        pending_cams = DBModel.fetch_all(
            "SELECT c.*, cu.name as customer_name FROM campaigns c "
            "JOIN customers cu ON c.customer_id = cu.id "
            "WHERE c.approval_status = 'pending' AND c.is_deleted = 0 AND c.customer_id = %s",
            (cust_id,)
        )
    
    # 3. Mẫu quảng cáo cần rà soát
    if role == 'admin':
        pending_creatives = DBModel.fetch_all(
            "SELECT cr.*, cam.name as campaign_name FROM creatives cr "
            "JOIN campaigns cam ON cr.campaign_id = cam.id "
            "WHERE cr.status = 'Chờ duyệt'"
        )
    elif role == 'marketer':
        pending_creatives = DBModel.fetch_all(
            "SELECT cr.*, cam.name as campaign_name FROM creatives cr "
            "JOIN campaigns cam ON cr.campaign_id = cam.id "
            "JOIN customers cu ON cam.customer_id = cu.id "
            "WHERE cr.status = 'Chờ duyệt' AND cu.marketer_id = %s",
            (user_id,)
        )
    else: # client
        pending_creatives = DBModel.fetch_all(
            "SELECT cr.*, cam.name as campaign_name FROM creatives cr "
            "JOIN campaigns cam ON cr.campaign_id = cam.id "
            "WHERE cr.status = 'Chờ duyệt' AND cam.customer_id = %s",
            (cust_id,)
        )
    
    # Convert transactions to dict for JSON serialization
    transactions_list = []
    for tx in pending_txs:
        transactions_list.append({
            'id': tx.id,
            'customer_name': tx.customer.name if tx.customer else 'N/A',
            'type': tx.type,
            'amount': float(tx.amount),
            'status': tx.status,
            'created_at': tx.created_at.strftime('%Y-%m-%d %H:%M:%S') if tx.created_at else None
        })
    
    return jsonify({
        'transactions': transactions_list,
        'campaigns': pending_cams,
        'creatives': pending_creatives,
        'total_pending': len(transactions_list) + len(pending_cams) + len(pending_creatives)
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
        SELECT u.id, u.username, u.username as full_name,
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


@admin_bp.route('/audit-logs')
@require_role_page(['admin'])
def audit_logs_page():
    """Trang hiển thị nhật ký hệ thống."""
    return render_template('admin/audit_logs.html')


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

    start_date = request.args.get('start_date')
    end_date   = request.args.get('end_date')

    # 1. CPL & Conversions & Total Spent
    where_clause = "WHERE c.customer_id = %s AND c.is_deleted = 0"
    params = [cust_id]

    if start_date and end_date:
        where_clause += " AND dr.report_date BETWEEN %s AND %s"
        params.extend([start_date, end_date])

    sql_metrics = f"""
        SELECT SUM(daily_spent) as total_spent,
               SUM(conversions) as total_conv,
               SUM(daily_spent) / NULLIF(SUM(conversions), 0) as cpl
        FROM daily_reports dr
        JOIN campaigns c ON dr.campaign_id = c.id
        {where_clause}
    """
    metrics = DBModel.fetch_one(sql_metrics, tuple(params))

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
    balance = float(cust.balance or 0)
    
    days_remaining = None
    if avg_daily_spend > 0:
        days_remaining = int(balance / avg_daily_spend)

    # 3. Over Budget Campaigns
    sql_over_budget = """
        SELECT name, budget, spent
        FROM campaigns
        WHERE customer_id = %s AND is_deleted = 0 AND spent >= budget AND budget > 0
    """
    over_budget_cams = DBModel.fetch_all(sql_over_budget, (cust_id,))
    for c in over_budget_cams:
        c['budget'] = float(c['budget'] or 0)
        c['spent'] = float(c['spent'] or 0)

    return jsonify({
        'total_conversions': int(metrics['total_conv'] or 0),
        'total_spent': float(metrics['total_spent'] or 0),
        'cpl': float(metrics['cpl'] or 0),
        'avg_daily_spend': avg_daily_spend,
        'balance': balance,
        'days_remaining': days_remaining,
        'over_budget_count': len(over_budget_cams),
        'over_budget_campaigns': over_budget_cams
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
    start_date = request.args.get('start_date')
    end_date   = request.args.get('end_date')
    
    cams   = CampaignModel.get_by_role(session['role'], session.get('customer_id'), session.get('user_id'))
    result = []

    for cam_obj in cams:
        # Convert to dict for compatibility and JSON serialization
        c = {
            'id': cam_obj.id,
            'name': cam_obj.name,
            'budget': float(cam_obj.budget or 0),
            'spent': float(cam_obj.spent or 0),
            'status': cam_obj.status,
            'approval_status': cam_obj.approval_status,
            'platform': cam_obj.platform,
            'target_link': cam_obj.target_link,
            'created_at': cam_obj.created_at.strftime('%Y-%m-%d %H:%M:%S') if cam_obj.created_at else None
        }

        # Nếu có khoảng thời gian, tính lại spent trong khoảng đó
        if start_date and end_date:
            sql_range_spent = """
                SELECT SUM(daily_spent) as range_spent 
                FROM daily_reports 
                WHERE campaign_id = %s AND report_date BETWEEN %s AND %s
            """
            row = DBModel.fetch_one(sql_range_spent, (c['id'], start_date, end_date))
            c['spent'] = float(row['range_spent'] or 0)

        # Thêm CTR/CPC và nhãn hiệu quả từ efficiency stats
        eff = CampaignModel.get_efficiency_stats(c['id'])
        if eff:
            c['ctr'] = eff['ctr']
            c['cpc'] = eff['cpc']
            c['efficiency_label'] = eff['label']
            c['efficiency_css']   = eff['label_css']
        else:
            c['ctr'] = 0
            c['cpc'] = 0
            c['efficiency_label'] = 'N/A'
            c['efficiency_css']   = 'bg-slate-100 text-slate-500'

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
@validate_schema(CampaignCreateSchema)
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
            cust = CustomerModel.get_by_id(old_val.customer_id)
            if not cust or cust.marketer_id != session.get('user_id'):
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
        return jsonify({'success': True, 'message': f'Đã xóa chiến dịch "{cam.name}" thành công!'})
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


@admin_bp.route('/transactions')
@require_role_page(['admin'])
def transaction_manage():
    """Trang quản lý nạp tiền (Admin)."""
    return render_template('admin/transaction_manage.html')


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
    try:
        users = UserModel.get_all()
        # Chuyển đổi created_at sang string
        for u in users:
            if u.get('created_at'):
                if hasattr(u['created_at'], 'strftime'):
                    u['created_at'] = u['created_at'].strftime('%Y-%m-%d %H:%M')
                else:
                    u['created_at'] = str(u['created_at'])
            else:
                u['created_at'] = '—'
        return jsonify(users)
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'message': f"Lỗi lấy danh sách user: {str(e)}", 'trace': traceback.format_exc()}), 500


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
        AuditLogModel.log(session['user_id'], 'CREATE_USER', 'users', None, None, {'username': username, 'role': role})
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
@require_role_api(['admin', 'marketer', 'client'])
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
        # KIỂM TRA TRẠNG THÁI DUYỆT
        cam_obj = CampaignModel.get_by_id(cam_id)
        if not cam_obj:
            return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404
            
        if cam_obj.status == 'Chờ duyệt' or cam_obj.approval_status == 'pending':
            return jsonify({'success': False, 'message': 'Không thể cập nhật chi phí cho chiến dịch chưa được duyệt!'}), 400

        # 1. Lưu vào daily_spending
        SpendingModel.log_daily_spending(cam_id, date, spent, clicks, impr)
        
        # 2. Đồng bộ tổng chi tiêu vào bảng campaigns.spent
        total_spent = SpendingModel.get_total_spent(cam_id)
        CampaignModel.update_spent(cam_id, total_spent)
        
        # 3. Kiểm tra ngân sách để gửi cảnh báo nếu cần
        cam_obj = CampaignModel.get_by_id(cam_id)
        if cam_obj:
            check_budget_and_notify(cam_obj, total_spent)
        
        return jsonify({'success': True, 'message': 'Đã cập nhật báo cáo thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/api/log-spending/recent')
@require_role_api(['admin', 'marketer'])
def get_recent_spending_logs():
    """Lấy danh sách các bản ghi chi tiêu mới nhập gần đây."""
    marketer_id = session['user_id'] if session['role'] == 'marketer' else None
    logs = SpendingModel.get_recent_logs(limit=10, marketer_id=marketer_id)
    # Serialize dates
    for l in logs:
        if l.get('report_date') and hasattr(l['report_date'], 'strftime'):
            l['report_date'] = l['report_date'].strftime('%Y-%m-%d')
    return jsonify(logs)


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
            marketer_id = old_val.marketer_id

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
    marketers = DBModel.fetch_all("SELECT id, username, username as full_name FROM users WHERE role = 'marketer' AND is_active = 1")
    return jsonify(marketers)


@admin_bp.route('/api/deposit', methods=['POST'])
@require_role_api(['client'])
@limiter.limit("5 per minute")
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
        return jsonify({'success': True, 'message': 'Yêu cầu nạp tiền đã được gửi, vui lòng chờ Admin phê duyệt.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500






@admin_bp.route('/api/transactions')
@require_role_api(['admin'])
def get_transactions():
    """API lấy danh sách giao dịch lọc theo status."""
    status = request.args.get('status')
    txs = TransactionModel.get_all(status=status)
    return jsonify(txs)


@admin_bp.route('/api/transactions/<int:tx_id>/approve', methods=['POST'])
@require_role_api(['admin', 'marketer'])
def approve_transaction(tx_id):
    """
    Phê duyệt giao dịch nạp tiền (Quy trình 2 lớp).
    - Marketer: Xác nhận chứng từ (pending -> confirmed)
    - Admin: Duyệt cộng tiền (confirmed -> completed)
    """
    tx = TransactionModel.get_by_id(tx_id)
    if not tx:
        return jsonify({'success': False, 'message': 'Giao dịch không tồn tại!'}), 404
        
    role = session.get('role')
    
    try:
        if role == 'marketer':
            if tx.status != 'pending':
                return jsonify({'success': False, 'message': 'Chỉ có thể xác nhận giao dịch đang chờ!'}), 400
            TransactionModel.update_status(tx_id, 'confirmed')
            AuditLogModel.log(session['user_id'], 'MARKETER_CONFIRM_DEPOSIT', 'transactions', tx_id)
            return jsonify({'success': True, 'message': 'Đã xác nhận chứng từ, chờ Admin phê duyệt cuối.'})
            
        elif role == 'admin':
            # Admin có thể duyệt thẳng hoặc duyệt từ confirmed
            if tx.status not in ['pending', 'confirmed']:
                return jsonify({'success': False, 'message': 'Giao dịch đã được xử lý!'}), 400
                
            # 1. Cập nhật số dư khách hàng
            CustomerModel.deposit(tx.customer_id, tx.amount)
            
            # 2. Cập nhật trạng thái giao dịch
            TransactionModel.update_status(tx_id, 'completed')
            
            # 3. Tạo thông báo & Socket.io
            socketio.emit('payment_approved', {
                'customer_id': tx.customer_id,
                'amount': tx.amount,
                'message': f'Nạp tiền thành công: {tx.amount:,.0f} VNĐ'
            })
            
            AuditLogModel.log(session['user_id'], 'ADMIN_APPROVE_DEPOSIT', 'transactions', tx_id)
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
    if not tx or tx.status != 'pending':
        return jsonify({'success': False, 'message': 'Giao dịch không hợp lệ hoặc đã xử lý!'}), 400
    
    try:
        TransactionModel.update_status(tx_id, 'rejected', reason)
        
        user = DBModel.fetch_one("SELECT id FROM users WHERE customer_id = %s", (tx.customer_id,))
        if user:
            NotificationModel.create(user['id'], "Yêu cầu nạp tiền bị từ chối", 
                                     f"Yêu cầu nạp {tx.amount:,.0f} VNĐ bị từ chối. Lý do: {reason}", "error")
            
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

    # KIỂM TRA TRẠNG THÁI DUYỆT
    if cam.status == 'Chờ duyệt' or cam.approval_status == 'pending':
        return jsonify({'success': False, 'message': 'Chiến dịch chưa được duyệt, không thể ghi nhận báo cáo!'}), 400

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
    new_spent = float(cam.spent or 0) + daily_spent
    budget    = float(cam.budget or 1)
    ratio     = new_spent / budget

    # Cập nhật spent
    DBModel.execute(
        "UPDATE campaigns SET spent = %s WHERE id = %s",
        (new_spent, campaign_id)
    )

    # Kiểm tra ngưỡng cảnh báo & Kill-switch
    from app.extensions import socketio

    # 1. Campaign Budget Alert
    if ratio >= 1.0:
        DBModel.execute("UPDATE campaigns SET status = 'Tạm dừng' WHERE id = %s", (campaign_id,))
        msg = f"Chiến dịch \"{cam.name}\" đã hết ngân sách. Tự động tạm dừng!"
        socketio.emit('budget_exceeded', {'campaign_id': campaign_id, 'message': msg})
    elif ratio >= 0.9:
        msg = f"Chiến dịch \"{cam.name}\" đã tiêu 90% ngân sách."
        socketio.emit('budget_warning', {'campaign_id': campaign_id, 'message': msg})

    # 2. Customer Balance Kill-switch
    cust = CustomerModel.get_by_id(cam.customer_id)
    if cust and float(cust.balance) <= 0:
        DBModel.execute("UPDATE campaigns SET status = 'Tạm dừng' WHERE customer_id = %s", (cust.id,))
        socketio.emit('balance_exhausted', {
            'customer_name': cust.name,
            'message': f'Khách hàng {cust.name} đã hết số dư. Tất cả chiến dịch đã dừng.'
        })

    AuditLogModel.log(session['user_id'], 'LOG_DAILY', 'daily_reports', campaign_id, None, 
                      {'daily_spent': daily_spent, 'total_spent': new_spent})

    return jsonify({'success': True, 'message': 'Ghi nhận báo cáo thành công!'})



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
            SELECT dr.report_date, SUM(dr.daily_spent) AS total_spent
            FROM   daily_reports dr
            JOIN   campaigns c ON dr.campaign_id = c.id
            WHERE  c.customer_id = %s AND c.is_deleted = 0
              AND  dr.report_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY dr.report_date
            ORDER BY dr.report_date ASC
        """
        rows = DBModel.fetch_all(sql, (cust_id,))
    elif role == 'marketer':
        user_id = session.get('user_id')
        sql = """
            SELECT dr.report_date, SUM(dr.daily_spent) AS total_spent
            FROM   daily_reports dr
            JOIN   campaigns c ON dr.campaign_id = c.id
            JOIN   customers cu ON c.customer_id = cu.id
            WHERE  cu.marketer_id = %s AND c.is_deleted = 0
              AND  dr.report_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY dr.report_date
            ORDER BY dr.report_date ASC
        """
        rows = DBModel.fetch_all(sql, (user_id,))
    else:
        sql = """
            SELECT dr.report_date, SUM(dr.daily_spent) AS total_spent
            FROM   daily_reports dr
            JOIN   campaigns c ON dr.campaign_id = c.id
            WHERE  c.is_deleted = 0
              AND  dr.report_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY dr.report_date
            ORDER BY dr.report_date ASC
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
    if role == 'client' and cam.customer_id != session.get('customer_id'):
        return "Unauthorized", 403
    
    # Check permission for marketer
    if role == 'marketer':
        cust = CustomerModel.get_by_id(cam.customer_id)
        if not cust or cust.marketer_id != user_id:
            return "Unauthorized", 403

    creatives  = CreativeModel.get_by_campaign(campaign_id)
    platforms  = CampaignPlatformModel.get_by_campaign(campaign_id)
    
    # [HOTFIX] Auto-migration: Nếu chưa có dữ liệu n-n nhưng campaign cũ có platform, tự động tạo record
    if not platforms and cam.platform:
        # Tìm platform_id từ tên
        p_row = DBModel.fetch_one("SELECT id FROM platforms WHERE name = %s", (cam.platform,))
        if not p_row:
            # Thử tìm tương đối nếu không khớp tuyệt đối
            p_row = DBModel.fetch_one("SELECT id FROM platforms WHERE name LIKE %s", (f"{cam.platform}%",))
            
        if p_row:
            CampaignPlatformModel.add(campaign_id, p_row['id'], cam.budget)
            platforms = CampaignPlatformModel.get_by_campaign(campaign_id)
    
    # Tính trạng thái thanh toán
    customer_balance = 0.0
    payment_status   = 'pending'
    if cam.customer_id:
        cust_data = CustomerModel.get_by_id(cam.customer_id)
        if cust_data:
            customer_balance = float(cust_data.balance or 0)
    if platforms:
        payment_status = CampaignPlatformModel.compute_payment_status(campaign_id, customer_balance)
        # Lưu lại vào DB nếu thay đổi (bọc trong try-except phòng trường hợp cột chưa tồn tại)
        try:
            if cam.payment_status != payment_status:
                DBModel.execute("UPDATE campaigns SET payment_status = %s WHERE id = %s",
                                (payment_status, campaign_id))
        except:
            pass
    
    # Tự động dừng nếu hết ngân sách (Enforce budget limit)
    if float(cam.spent or 0) >= float(cam.budget or 0.1) and cam.status == 'Đang chạy':
        try:
            DBModel.execute("UPDATE campaigns SET status = 'Hết ngân sách' WHERE id = %s", (campaign_id,))
            cam.status = 'Hết ngân sách'
        except:
            pass
    
    from app.models.daily_report import DailyReportModel
    metrics = DailyReportModel.get_total_metrics(campaign_id)
    raw_logs = DailyReportModel.get_last_7_days(campaign_id)
    
    # Map keys for template compatibility (amount_spent)
    logs = []
    for l in raw_logs:
        logs.append({
            'date': l['report_date'],
            'amount_spent': l['daily_spent'],
            'clicks': l['clicks']
        })
    
    # Nếu chưa duyệt, zero out metrics
    if cam.status == 'Chờ duyệt' or cam.approval_status == 'pending':
        metrics = {'total_clicks': 0, 'total_impressions': 0, 'total_conversions': 0}
        logs    = []
    
    return render_template('admin/campaign_detail.html',
                           campaign=cam,
                           creatives=creatives,
                           platforms=platforms,
                           payment_status=payment_status,
                           customer_balance=customer_balance,
                           metrics=metrics,
                           logs=logs)


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
        AuditLogModel.log(session['user_id'], 'APPROVE_CAMPAIGN', 'campaigns', campaign_id, cam.approval_status, 'active')
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
        AuditLogModel.log(session['user_id'], 'REJECT_CAMPAIGN', 'campaigns', campaign_id, cam.approval_status, 'paused')
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


# ─────────────────────────────────────────────────────────────────────────────
# API — Multi-Platform Campaign Management
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/campaigns/<int:campaign_id>/platforms', methods=['GET'])
@require_role_api(['admin', 'marketer', 'client'])
def get_campaign_platforms(campaign_id):
    """Lấy danh sách nền tảng và thống kê hiệu quả của một chiến dịch."""
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404

    # Kiểm tra quyền
    if session['role'] == 'client' and cam['customer_id'] != session.get('customer_id'):
        return jsonify({'success': False, 'message': 'Không có quyền truy cập!'}), 403

    platforms = CampaignPlatformModel.get_by_campaign(campaign_id)
    
    # Serialize datetime
    for p in platforms:
        if p.get('created_at') and hasattr(p['created_at'], 'strftime'):
            p['created_at'] = p['created_at'].strftime('%Y-%m-%d %H:%M')

    return jsonify({'success': True, 'data': platforms})


@admin_bp.route('/api/campaigns/<int:campaign_id>/platforms/add', methods=['POST'])
@require_role_api(['admin', 'marketer'])
def add_campaign_platform(campaign_id):
    """Thêm một nền tảng vào chiến dịch với ngân sách phân bổ riêng."""
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404

    data        = request.json or {}
    platform_id = data.get('platform_id')
    budget_alloc = float(data.get('budget_alloc') or 0)

    if not platform_id:
        return jsonify({'success': False, 'message': 'Vui lòng chọn nền tảng!'}), 400
    if budget_alloc <= 0:
        return jsonify({'success': False, 'message': 'Ngân sách phân bổ phải là số dương!'}), 400

    # Kiểm tra tổng ngân sách phân bổ không vượt ngân sách chiến dịch
    current_alloc = CampaignPlatformModel.get_total_alloc(campaign_id)
    if current_alloc + budget_alloc > float(cam['budget']):
        return jsonify({
            'success': False,
            'message': f'Tổng ngân sách phân bổ ({(current_alloc + budget_alloc)/1e6:.1f}M) vượt quá ngân sách chiến dịch ({float(cam["budget"])/1e6:.1f}M)!'
        }), 400

    try:
        plat = PlatformModel.get_by_id(platform_id)
        if not plat:
            return jsonify({'success': False, 'message': 'Nền tảng không tồn tại!'}), 404

        CampaignPlatformModel.add(campaign_id, platform_id, budget_alloc)
        AuditLogModel.log(session['user_id'], 'ADD_CAMPAIGN_PLATFORM', 'campaign_platforms', campaign_id, None,
                          {'platform_id': platform_id, 'budget_alloc': budget_alloc})
        return jsonify({'success': True, 'message': f'Đã thêm nền tảng {plat["name"]} với ngân sách {budget_alloc/1e6:.1f}M!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/campaigns/<int:campaign_id>/platforms/<int:platform_id>/remove', methods=['DELETE'])
@require_role_api(['admin', 'marketer'])
def remove_campaign_platform(campaign_id, platform_id):
    """Xóa một nền tảng khỏi chiến dịch."""
    try:
        CampaignPlatformModel.remove(campaign_id, platform_id)
        AuditLogModel.log(session['user_id'], 'REMOVE_CAMPAIGN_PLATFORM', 'campaign_platforms', campaign_id, None,
                          {'platform_id': platform_id})
        return jsonify({'success': True, 'message': 'Đã xóa nền tảng khỏi chiến dịch!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/campaigns/<int:campaign_id>/platforms/<int:cp_id>/update', methods=['PUT'])
@require_role_api(['admin', 'marketer'])
def update_campaign_platform(campaign_id, cp_id):
    """Cập nhật ngân sách phân bổ hoặc trạng thái của một nền tảng."""
    data   = request.json or {}
    cp_rec = CampaignPlatformModel.get_by_id(cp_id)
    if not cp_rec or cp_rec['campaign_id'] != campaign_id:
        return jsonify({'success': False, 'message': 'Không tìm thấy bản ghi!'}), 404

    try:
        if 'budget_alloc' in data:
            CampaignPlatformModel.update_budget(campaign_id, cp_rec['platform_id'], float(data['budget_alloc']))
        if 'status' in data and data['status'] in ('active', 'paused', 'completed'):
            CampaignPlatformModel.update_status(cp_id, data['status'])
        return jsonify({'success': True, 'message': 'Cập nhật thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/campaigns/<int:campaign_id>/results')
@require_role_api(['admin', 'marketer', 'client'])
def get_campaign_results(campaign_id):
    """Kết quả chiến dịch: biểu đồ chi tiêu + chỉ số tổng hợp theo nền tảng."""
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404

    if session['role'] == 'client' and cam.customer_id != session.get('customer_id'):
        return jsonify({'success': False, 'message': 'Không có quyền!'}), 403

    # Nếu chiến dịch chưa được duyệt, trả về kết quả trống
    if cam.status == 'Chờ duyệt' or cam.approval_status == 'pending':
        return jsonify({
            'success': True,
            'chart': {'dates': [], 'by_platform': {}},
            'summary': {
                'total_budget': float(cam.budget or 0),
                'total_spent': 0,
                'total_clicks': 0,
                'total_impressions': 0,
                'ctr': 0,
                'cpc': 0,
                'spent_pct': 0,
            },
            'platforms': [],
        })

    days = int(request.args.get('days', 30))
    
    # 1. Dữ liệu biểu đồ theo ngày × nền tảng
    chart_raw = CampaignPlatformModel.get_daily_chart_data(campaign_id, days)
    
    # FALLBACK: Nếu không có dữ liệu chi tiêu theo nền tảng, lấy dữ liệu tổng từ daily_reports
    if not chart_raw:
        from app.models.daily_report import DailyReportModel
        trend = DailyReportModel.get_last_7_days(campaign_id) # Trả về list dict với report_date, daily_spent...
        chart_raw = []
        for t in trend:
            chart_raw.append({
                'date': t['report_date'],
                'platform_name': 'Tổng hợp (Global)',
                'daily_spent': t['daily_spent'],
                'daily_clicks': t['clicks'],
                'daily_impressions': t['impressions']
            })

    # Pivot: { platform_name: { date: { spent, clicks, impressions } } }
    chart_by_platform = {}
    
    # Đảm bảo date là string YYYY-MM-DD
    processed_chart_raw = []
    for r in chart_raw:
        d_val = r['date']
        if hasattr(d_val, 'strftime'):
            d_str = d_val.strftime('%Y-%m-%d')
        else:
            d_str = str(d_val)
        
        processed_chart_raw.append({
            'date_str': d_str,
            'platform_name': r['platform_name'],
            'spent': float(r['daily_spent'] or 0),
            'clicks': int(r['daily_clicks'] or 0),
            'impressions': int(r['daily_impressions'] or 0)
        })

    all_dates = sorted(list(set(r['date_str'] for r in processed_chart_raw)))
    
    for r in processed_chart_raw:
        pname = r['platform_name']
        dstr  = r['date_str']
        if pname not in chart_by_platform:
            chart_by_platform[pname] = {}
        chart_by_platform[pname][dstr] = {
            'spent':       r['spent'],
            'clicks':      r['clicks'],
            'impressions': r['impressions'],
        }

    # 2. Tổng hợp theo nền tảng
    platforms_stats = CampaignPlatformModel.get_by_campaign(campaign_id)
    
    # 3. Tổng toàn chiến dịch
    total_clicks      = float(sum(p.get('total_clicks', 0) for p in platforms_stats))
    total_impressions = float(sum(p.get('total_impressions', 0) for p in platforms_stats))
    
    # FALLBACK cho summary nếu chưa có platform stats
    if not platforms_stats or (total_clicks == 0 and total_impressions == 0):
        m = DailyReportModel.get_total_metrics(campaign_id)
        total_clicks = float(m['total_clicks'] or 0)
        total_impressions = float(m['total_impressions'] or 0)
    total_spent       = float(cam.spent or 0)
    total_budget      = float(cam.budget or 1)

    # Serialize datetime
    for p in platforms_stats:
        if p.get('created_at') and hasattr(p['created_at'], 'strftime'):
            p['created_at'] = p['created_at'].strftime('%Y-%m-%d')

    return jsonify({
        'success': True,
        'chart': {
            'dates':       all_dates,
            'by_platform': chart_by_platform,
        },
        'summary': {
            'total_budget':      total_budget,
            'total_spent':       total_spent,
            'total_clicks':      int(total_clicks),
            'total_impressions': int(total_impressions),
            'ctr':    round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0,
            'cpc':    round(total_spent / total_clicks) if total_clicks > 0 else 0,
            'spent_pct': round(total_spent / total_budget * 100, 1),
        },
        'platforms': platforms_stats,
    })


@admin_bp.route('/api/campaigns/<int:campaign_id>/payment-status')
@require_role_api(['admin', 'marketer', 'client'])
def get_payment_status(campaign_id):
    """Trạng thái thanh toán của chiến dịch."""
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404

    if session['role'] == 'client' and cam.customer_id != session.get('customer_id'):
        return jsonify({'success': False, 'message': 'Không có quyền!'}), 403

    customer_balance = 0.0
    if cam.customer_id:
        cust_data = CustomerModel.get_by_id(cam.customer_id)
        if cust_data:
            customer_balance = float(cust_data.balance or 0)

    total_alloc    = CampaignPlatformModel.get_total_alloc(campaign_id)
    payment_status = CampaignPlatformModel.compute_payment_status(campaign_id, customer_balance)
    shortfall      = max(0, total_alloc - customer_balance)

    return jsonify({
        'success':         True,
        'payment_status':  payment_status,
        'customer_balance': customer_balance,
        'total_alloc':     total_alloc,
        'shortfall':       shortfall,
    })


@admin_bp.route('/api/campaigns/add-v2', methods=['POST'])
@require_role_api(['admin', 'marketer', 'client'])
def add_campaign_v2():
    """Tạo chiến dịch với nhiều nền tảng cùng lúc (phiên bản mới)."""
    data = request.json or {}

    name        = (data.get('name') or '').strip()
    objective   = (data.get('objective') or '').strip()
    customer_id = data.get('customer_id')
    budget      = data.get('budget')
    start_date  = data.get('start_date') or None
    end_date    = data.get('end_date')   or None
    target_link = (data.get('target_link') or '').strip()
    platforms   = data.get('platforms', [])  # [{platform_id, budget_alloc}, ...]

    # Creative fields
    creative_title = (data.get('creative_title') or name).strip()
    creative_desc  = (data.get('creative_desc') or '').strip()
    media_url      = (data.get('media_url') or '').strip()
    media_type     = (data.get('media_type') or 'image').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Tên chiến dịch không được để trống!'}), 400
    if not customer_id:
        return jsonify({'success': False, 'message': 'Vui lòng chọn khách hàng!'}), 400
    if not platforms:
        return jsonify({'success': False, 'message': 'Vui lòng chọn ít nhất 1 nền tảng!'}), 400

    try:
        budget = float(budget)
        if budget <= 0:
            return jsonify({'success': False, 'message': 'Ngân sách phải là số dương!'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Ngân sách không hợp lệ!'}), 400

    # Validate phân bổ ngân sách
    total_alloc = sum(float(p.get('budget_alloc', 0)) for p in platforms)
    if total_alloc > budget:
        return jsonify({'success': False, 'message': f'Tổng ngân sách phân bổ ({total_alloc:,.0f}) vượt quá ngân sách chiến dịch ({budget:,.0f})!'}), 400

    if start_date and end_date:
        try:
            if datetime.strptime(start_date, '%Y-%m-%d') >= datetime.strptime(end_date, '%Y-%m-%d'):
                return jsonify({'success': False, 'message': 'Ngày bắt đầu phải trước ngày kết thúc!'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Định dạng ngày không hợp lệ!'}), 400

    try:
        # Lấy tên nền tảng đầu tiên cho cột platform cũ (backward compat)
        first_platform = PlatformModel.get_by_id(platforms[0]['platform_id'])
        platform_name  = first_platform['name'] if first_platform else 'Multi-Platform'

        # 1. Tạo Campaign
        new_id = CampaignModel.create(name, customer_id, platform_name, budget, start_date, end_date, target_link, objective)

        # 2. Thêm từng nền tảng
        for p_item in platforms:
            CampaignPlatformModel.add(new_id, int(p_item['platform_id']), float(p_item.get('budget_alloc', 0)))

        # 3. Tạo Creative mặc định
        if creative_title:
            CreativeModel.create(new_id, creative_title, media_type, media_url, creative_desc)

        AuditLogModel.log(session['user_id'], 'CREATE_CAMPAIGN_MULTIPLATFORM', 'campaigns', new_id, None,
                          {'name': name, 'platforms': platforms, 'budget': budget})

        return jsonify({'success': True, 'message': f'Đã tạo chiến dịch "{name}" trên {len(platforms)} nền tảng!', 'id': new_id})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500

@admin_bp.route('/api/dashboard/smart-stats')
@require_role_api(['admin', 'marketer'])
def get_smart_stats():
    """Lấy các chỉ số thông minh cho Dashboard: Xu hướng, Cảnh báo, Dự báo."""
    try:
        # 1. Tổng ngân sách & Chi tiêu (toàn hệ thống)
        managed = DailyReportModel.get_total_managed_budget()
        total_budget = float(managed['total_budget'] or 0)
        total_spent   = float(managed['total_spent'] or 0)
        
        # 2. Đếm các yêu cầu chờ xử lý & Chiến dịch chạy
        pending_tx = DBModel.fetch_one("SELECT COUNT(*) as count FROM transactions WHERE status = 'pending'")
        pending_cams = DBModel.fetch_one("SELECT COUNT(*) as count FROM campaigns WHERE status = 'Đang chờ duyệt' AND is_deleted = 0")
        active_cams = DBModel.fetch_one("SELECT COUNT(*) as count FROM campaigns WHERE status = 'Đang chạy' AND is_deleted = 0")
        
        # 3. Biến động CPC/CPA
        fluctuations = DailyReportModel.get_cpc_cpa_fluctuations()
        
        # 4. Dự báo dòng tiền
        cashflow = DailyReportModel.get_cashflow_forecast()

        return jsonify({
            'success': True,
            'managed': {
                'total_budget': total_budget,
                'total_spent': total_spent,
                'spent_ratio': round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0
            },
            'pending_count': (pending_tx['count'] or 0) + (pending_cams['count'] or 0),
            'active_count': active_cams['count'] or 0,
            'fluctuations': fluctuations,
            'cashflow': cashflow
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


from app.extensions import db, migrate, socketio, csrf


@admin_bp.route('/api/campaigns/<int:campaign_id>/apply-ai', methods=['POST'])
@csrf.exempt
@require_role_api(['admin', 'marketer', 'client'])
def apply_ai_optimization(campaign_id):
    """
    Giả lập tối ưu hóa AI: Tăng số lượt click và chi tiêu cho chiến dịch.
    Điều này giúp hiển thị dữ liệu trên biểu đồ và tăng kết quả thực tế.
    """
    cam = CampaignModel.get_by_id(campaign_id)
    if not cam:
        return jsonify({'success': False, 'message': 'Không tìm thấy chiến dịch!'}), 404

    try:
        from datetime import datetime, timedelta
        import random
        
        # Tạo dữ liệu giả cho 7 ngày gần nhất nếu chưa có, hoặc cộng dồn nếu đã có
        total_added_spent = 0
        for i in range(6, -1, -1):
            report_date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # Giả lập tăng trưởng: ngày càng tăng clicks
            base_clicks = 10 + (6-i)*5 
            added_clicks = random.randint(base_clicks, base_clicks + 10)
            added_spent = added_clicks * random.randint(1000, 2500) # CPC từ 1k-2.5k
            added_impressions = added_clicks * random.randint(15, 40) # CTR 2.5-6.6%
            added_conversions = random.randint(0, max(1, added_clicks // 15))
            
            DailyReportModel.log_daily(campaign_id, report_date, added_spent, added_clicks, added_impressions, added_conversions)
            total_added_spent += added_spent
            
        # 1. Cập nhật spent tổng của campaign
        DBModel.execute("UPDATE campaigns SET spent = COALESCE(spent, 0) + %s WHERE id = %s", (total_added_spent, campaign_id))
        
        # 2. Kiểm tra ngân sách để dừng chiến dịch nếu vượt quá
        cam_updated = CampaignModel.get_by_id(campaign_id)
        budget = float(cam_updated['budget'] or 0)
        spent  = float(cam_updated['spent'] or 0)
        
        if spent >= budget:
            DBModel.execute("UPDATE campaigns SET status = 'Hết ngân sách' WHERE id = %s", (campaign_id,))
            
            # Gửi thông báo qua Socket.io
            msg = f"Chiến dịch \"{cam_updated['name']}\" đã tiêu hết ngân sách ({spent:,.0f}/{budget:,.0f}đ). Hệ thống đã tự động dừng chạy!"
            socketio.emit('budget_exceeded', {
                'campaign_id': campaign_id,
                'message': msg,
                'customer_id': cam_updated['customer_id']
            })
            
            # Tạo thông báo trong DB cho khách hàng
            from app.models.notification import NotificationModel
            cust_user = DBModel.fetch_one("SELECT id FROM users WHERE customer_id = %s", (cam_updated['customer_id'],))
            if cust_user:
                NotificationModel.create(cust_user['id'], "Hết ngân sách quảng cáo", msg, "error")

        return jsonify({
            'success': True, 
            'message': 'Hệ thống AI đã tối ưu hóa. ' + ('Cảnh báo: Chiến dịch đã dừng do hết ngân sách!' if spent >= budget else 'Hiệu suất đã được cải thiện!')
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
