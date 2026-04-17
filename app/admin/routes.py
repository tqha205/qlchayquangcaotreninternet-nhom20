from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from app.models import DBModel, CampaignModel
from functools import wraps

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
def restrict_access():
    if 'user_id' not in session:
        if request.path.startswith('/admin/api'):
            return jsonify({'success': False, 'message': 'Hết hạn đăng nhập!'}), 401
        return redirect(url_for('public.login_page'))
    
    if session.get('role') == 'client' and not request.path.startswith('/admin/api'):
        return redirect(url_for('public.index'))

# Middleware cho API
def require_role(roles):
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

@admin_bp.route('/dashboard')
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/campaigns')
def campaigns():
    return render_template('admin/campaigns.html')

@admin_bp.route('/api/stats')
@require_role(['admin', 'marketer', 'client'])
def get_stats():
    role = session['role']
    id = session['customer_id']
    # Logic thống kê từ models
    # (Để đơn giản hóa, ta sử dụng DBModel.fetch_one trực tiếp hoặc mở rộng thêm model)
    stats = {}
    if role == 'client' and id:
        res = DBModel.fetch_one("SELECT COUNT(*) as cnt, SUM(budget) as b, SUM(spent) as s FROM campaigns WHERE customer_id = %s", (id,))
        stats = {'total_campaigns': res['cnt'], 'total_budget': float(res['b'] or 0), 'total_spent': float(res['s'] or 0), 'total_customers': 1}
    else:
        res = DBModel.fetch_one("SELECT COUNT(*) as cnt, SUM(budget) as b, SUM(spent) as s FROM campaigns")
        cust_cnt = DBModel.fetch_one("SELECT COUNT(*) as cnt FROM customers")['cnt']
        stats = {'total_campaigns': res['cnt'], 'total_budget': float(res['b'] or 0), 'total_spent': float(res['s'] or 0), 'total_customers': cust_cnt}
    return jsonify(stats)

@admin_bp.route('/api/campaigns')
@require_role(['admin', 'marketer', 'client'])
def get_campaigns():
    cams = CampaignModel.get_by_role(session['role'], session['customer_id'])
    return jsonify(cams)
