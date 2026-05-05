from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import InquiryModel
from app.models.base import DBModel

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    # Lấy số liệu thực tế từ DB cho Stats Bar
    try:
        budget_row = DBModel.fetch_one("SELECT COALESCE(SUM(budget), 0) AS total FROM campaigns WHERE is_deleted = 0")
        running_row = DBModel.fetch_one("SELECT COUNT(*) AS total FROM campaigns WHERE status = 'Đang chạy' AND is_deleted = 0")
        customers_row = DBModel.fetch_one("SELECT COUNT(*) AS total FROM customers")

        stats = {
            'total_budget':    int(budget_row['total'] if budget_row else 0),
            'active_cams': int(running_row['total'] if running_row else 0),
            'total_customers': int(customers_row['total'] if customers_row else 0),
        }
    except Exception:
        # Fallback dữ liệu nếu DB chưa có hoặc lỗi
        stats = {
            'total_budget': 5200000000, 
            'active_cams': 48, 
            'total_customers': 312
        }

    return render_template('public/index.html', stats=stats)



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

@public_bp.route('/blog/<path:slug>')
def blog_post(slug):
    # Dữ liệu giả lập cho bài viết/video
    post_data = {
        'title': 'Bí mật chạy quảng cáo ra trăm đơn mỗi ngày',
        'content': 'Đây là nội dung chi tiết của bài viết được hiển thị khi click từ menu hoặc trang chủ.',
        'has_video': True,
        'video_url': 'https://www.youtube.com/embed/dQw4w9WgXcQ' # sample video
    }
    return render_template('public/blog_post.html', post=post_data, slug=slug)

@public_bp.route('/web-design/theme/<path:theme_slug>')
def theme_detail(theme_slug):
    # Dữ liệu giả lập, trong thực tế sẽ truy vấn từ DB theo theme_slug
    theme = {
        'title': 'WEBSITE BẤT ĐỘNG SẢN – BDS05',
        'price': '3.099.000 VNĐ',
        'category': 'Gói PRO, Website bất động sản',
        'image': 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&q=80&w=1200',
        'description': 'Thiết kế website bất động sản BDS05 dành riêng cho loại hình một dự án. Đáp ứng nhu cầu cho cá nhân và doanh nghiệp muốn phát triển một dự án chuyên nghiệp. Mẫu website BDS05 được thiết kế chuẩn SEO, tương thích mọi thiết bị và tối ưu cho quảng cáo.',
        'slug': theme_slug
    }
    return render_template('public/theme_detail.html', theme=theme)

@public_bp.route('/web-design/package/<path:package_type>')
def service_package(package_type):
    titles = {
        'goi-website-basic': 'Gói BASIC',
        'goi-website-pro': 'Gói PRO',
        'goi-website-business': 'Gói BUSINESS'
    }
    title = titles.get(package_type, 'Thiết kế Website')
    
    # Xác định theme và thông tin dựa trên slug
    badge_label = 'Basic'
    badge_color = 'bg-red-500' # Theo ảnh thiết kế Basic thì badge hình sao nền đỏ "Basic"
    price_tag = '1.599.000 VNĐ'
    
    if 'pro' in package_type:
        badge_label = 'Pro'
        badge_color = 'bg-yellow-500 text-slate-900'
        price_tag = '3.099.000 VNĐ'
    elif 'business' in package_type:
        badge_label = 'Business'
        badge_color = 'bg-purple-600'
        price_tag = '5.899.000 VNĐ'
        
    return render_template('public/service_package.html', 
                          package_type=package_type, 
                          title=title, 
                          badge_label=badge_label,
                          badge_color=badge_color,
                          price_tag=price_tag)

@public_bp.route('/services/<path:service_slug>')
def service_detail(service_slug):
    if service_slug == 'facebook-ads':
        return render_template('public/facebook_ads.html')
    elif service_slug == 'google-ads':
        return render_template('public/google_ads.html')
    elif service_slug == 'zalo-ads':
        return render_template('public/zalo_ads.html')
    elif service_slug == 'quet-so-dien-thoai':
        return render_template('public/phone_scan.html')
    
    # Default to 404 or generic for now if others are clicked
    return "Đang cập nhật", 200

