from flask import Blueprint, request, jsonify, session, redirect, url_for
from app.models import UserModel, DBModel
import mysql.connector
from pydantic import ValidationError
from app.forms import LoginSchema, RegisterSchema

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = LoginSchema(**(request.json or {}))
    except ValidationError as e:
        return jsonify({'success': False, 'message': 'Dữ liệu đầu vào không hợp lệ!'}), 400

    username = data.username.strip()
    password = data.password

    user = UserModel.get_by_auth(username, password)

    if user:
        session.permanent = True
        session['user_id']    = user['id']
        session['role']       = user['role']
        session['username']   = user['username']      # Lưu username để hiển thị trên sidebar
        session['customer_id'] = user['customer_id']
        return jsonify({
            'success': True,
            'role': user['role'],
            'customer_id': user['customer_id']
        })

    return jsonify({'success': False, 'message': 'Tài khoản hoặc mật khẩu không chính xác!'}), 401


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = RegisterSchema(**(request.json or {}))
    except ValidationError as e:
        return jsonify({'success': False, 'message': 'Vui lòng kiểm tra lại thông tin (Username >= 3, Password >= 6)!'}), 400

    try:
        user_id = UserModel.create_client(
            data.username.strip(),
            data.password,
            data.full_name.strip(),
            data.email,
            data.phone
        )

        if user_id:
            # Lấy thông tin đầy đủ của user vừa tạo
            user = UserModel.get_by_id(user_id)
            session.permanent = True
            session['user_id']    = user['id']
            session['role']       = user['role']
            session['username']   = user['username']
            session['customer_id'] = user['customer_id']
            return jsonify({'success': True})

    except mysql.connector.IntegrityError:
        # Trùng username (UNIQUE constraint)
        return jsonify({'success': False, 'message': 'Tên đăng nhập đã tồn tại, vui lòng chọn tên khác!'}), 409

    except Exception as e:
        return jsonify({'success': False, 'message': f'Có lỗi xảy ra: {str(e)}'}), 500


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('public.login_page'))

