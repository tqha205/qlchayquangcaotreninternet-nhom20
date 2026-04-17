from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import InquiryModel

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    return render_template('public/index.html')

@public_bp.route('/pricing')
def pricing():
    return render_template('public/pricing.html')

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'service': request.form.get('service'),
            'message': request.form.get('message')
        }
        InquiryModel.create(data)
        flash('Yêu cầu đã được gửi! Chúng tôi sẽ liên hệ lại sớm nhất.', 'success')
        return redirect(url_for('public.contact'))
    return render_template('public/contact.html')

@public_bp.route('/login')
def login_page():
    return render_template('auth/login.html')
@public_bp.route('/register')
def register_page():
    return render_template('auth/register.html')
