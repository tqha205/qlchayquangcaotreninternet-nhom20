from flask import Blueprint, request, jsonify, session, redirect, url_for
from app.models import UserModel, DBModel

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    user = UserModel.get_by_auth(data.get('username'), data.get('password'))
    
    if user:
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['customer_id'] = user['customer_id']
        return jsonify({
            'success': True, 
            'role': user['role'],
            'customer_id': user['customer_id']
        })
    return jsonify({'success': False, 'message': 'Tài khoản hoặc mật khẩu không chính xác!'}), 401

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    try:
        user_id = UserModel.create_client(
            data.get('username'),
            data.get('password'),
            data.get('full_name'),
            data.get('email'),
            data.get('phone')
        )
        # Tự động đăng nhập sau khi đăng ký
        if user_id:
            # Lấy thông tin đầy đủ của user vừa tạo
            user = DBModel.fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['customer_id'] = user['customer_id']
            return jsonify({'success': True})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('public.login_page'))
