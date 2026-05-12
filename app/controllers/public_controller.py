from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
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

@public_bp.route('/about')
def about():
    return render_template('public/about.html')



from app.extensions import limiter
from app.tasks import send_telegram
import logging

@public_bp.route('/contact', methods=['GET'])
def contact():
    return render_template('public/contact.html')


@public_bp.route('/contact', methods=['POST'])
@limiter.limit("5 per hour")
def contact_submit():
    # 1. Honeypot check
    honeypot = request.form.get('website')  # Field ẩn tên 'website'
    if honeypot:
        logging.warning(f"Spam detected from {request.remote_addr}")
        return jsonify({'success': False, 'message': 'Spam detected!'}), 400

    data = {
        'name': request.form.get('name'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'service': request.form.get('service'),
        'message': request.form.get('message')
    }

    # Validate simple
    if not data['name'] or not data['phone']:
        return jsonify({'success': False, 'message': 'Vui lòng điền đầy đủ Tên và Số điện thoại!'}), 400

    try:
        # 2. Save to DB
        inquiry_id = InquiryModel.create(data)

        # 3. Send Notifications (Async) — bỏ qua nếu Celery/Redis chưa sẵn sàng
        try:
            admin_msg = f"🔔 *Yêu cầu tư vấn mới*\n👤: {data['name']}\n📞: {data['phone']}\n📧: {data['email']}\n🛠: {data['service']}\n📝: {data['message']}"
            send_telegram.delay(admin_msg)
        except Exception:
            logging.warning("Telegram notification skipped (Celery/Redis not available)")

        # Giả lập gửi email cảm ơn (Cần cấu hình Flask-Mail để chạy thực)
        logging.info(f"Email cảm ơn đã được xếp hàng gửi tới {data['email']}")

        return jsonify({
            'success': True,
            'message': 'Cảm ơn bạn đã liên hệ! Chúng tôi sẽ phản hồi trong vòng 24h.'
        })
    except Exception as e:
        logging.error(f"Error in contact form: {e}")
        return jsonify({'success': False, 'message': 'Có lỗi xảy ra, vui lòng thử lại sau.'}), 500

@public_bp.route('/login')
def login_page():
    return render_template('auth/login.html')

@public_bp.route('/register')
def register_page():
    return render_template('auth/register.html')

@public_bp.route('/blog')
def blog_list():
    # Danh sách bài viết để hiển thị ở trang danh sách
    blogs = {
        'tin-tuc-digital-marketing': {
            'title': 'Xu hướng Digital Marketing bùng nổ trong năm 2026',
            'content': 'Khám phá sự lên ngôi của AI và chiến lược cá nhân hóa trong kỷ nguyên số.',
            'category': 'Tin tức',
            'image': 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80'
        },
        'kien-thuc-facebook-ads': {
            'title': 'Bí kíp tối ưu Facebook Ads giúp X3 doanh số',
            'content': 'Cách tận dụng Reels và thuật toán Meta để bứt phá doanh thu bán hàng.',
            'category': 'Kiến thức',
            'image': 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=800&q=80'
        },
        'kien-thuc-google-ads': {
            'title': 'Google Ads chuyên sâu: Chinh phục Performance Max',
            'content': 'Làm chủ hệ sinh thái quảng cáo của Google với sức mạnh từ trí tuệ nhân tạo.',
            'category': 'Kiến thức',
            'image': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80'
        },
        'kien-thuc-zalo-ads': {
            'title': 'Zalo Ads: Kênh tiếp cận khách hàng Việt hiệu quả nhất',
            'content': 'Khai phá tiềm năng từ ứng dụng nhắn tin quốc dân với hơn 70 triệu người dùng.',
            'category': 'Kiến thức',
            'image': 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800&q=80'
        },
        'kien-thuc-tiktok-ads': {
            'title': 'TikTok Ads: Chinh phục khách hàng qua video ngắn',
            'content': 'Biến nội dung giải trí thành cỗ máy bán hàng tự động trên nền tảng hot nhất hiện nay.',
            'category': 'Chiến thuật',
            'image': 'https://images.unsplash.com/photo-1611605698335-8b1569810432?w=800&q=80'
        }
    }
    return render_template('public/blog_list.html', blogs=blogs)

@public_bp.route('/blog/<path:slug>')
def blog_post(slug):
    # Dữ liệu giả lập chi tiết cho các bài viết
    blogs = {
        'tin-tuc-digital-marketing': {
            'title': 'Xu hướng Digital Marketing bùng nổ trong năm 2026',
            'content': 'Năm 2026 đánh dấu sự lên ngôi của AI và cá nhân hóa trải nghiệm khách hàng.',
            'full_text': '<p>Năm 2026, thế giới Digital Marketing đang chứng kiến những bước ngoặt vĩ đại. Trí tuệ nhân tạo (AI) không còn là một công cụ hỗ trợ mà đã trở thành "trái tim" của mọi chiến dịch.</p><h2>Sự lên ngôi của cá nhân hóa quy mô lớn</h2><p>Các thuật toán hiện nay có khả năng phân tích hàng tỷ điểm dữ liệu để tạo ra những thông điệp quảng cáo duy nhất cho từng cá nhân. Điều này giúp tăng tỷ lệ chuyển đổi lên gấp 5 lần so với phương pháp truyền thống.</p><h3>Chiến lược ưu tiên dữ liệu thực</h3><p>HTDADS Agency luôn khuyến khích khách hàng tập trung vào First-party Data để đảm bảo tính bền vững và tuân thủ các quy định về quyền riêng tư ngày càng khắt khe.</p>',
            'category': 'Tin tức',
            'author': 'Nguyễn Văn A',
            'image': 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1600&q=80'
        },
        'kien-thuc-facebook-ads': {
            'title': 'Bí kíp tối ưu Facebook Ads giúp X3 doanh số',
            'content': 'Facebook Ads vẫn là kênh mang lại hiệu quả cao nếu bạn biết cách tối ưu định dạng Video ngắn.',
            'full_text': '<p>Facebook trong năm 2026 đã thay đổi hoàn toàn cách tiếp cận người dùng. Định dạng Reels và Video ngắn đang chiếm tới 80% thời gian tương tác trên nền tảng.</p><h2>Tối ưu hóa nội dung sáng tạo (Creative First)</h2><p>Thuật toán Meta hiện nay ưu tiên những nội dung có khả năng giữ chân người dùng lâu nhất. Việc sử dụng AI để tạo ra các mẫu quảng cáo động (Dynamic Creative) là bắt buộc nếu bạn muốn cạnh tranh về giá thầu.</p><h3>Kỹ thuật nhắm mục tiêu Advantage+</h3><p>Chúng tôi đã thử nghiệm và thấy rằng việc để thuật toán tự tìm kiếm khách hàng mang lại ROI cao hơn 30% so với việc nhắm mục tiêu thủ công truyền thống.</p>',
            'category': 'Kiến thức',
            'author': 'Trần Thị B',
            'image': 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=1600&q=80'
        },
        'kien-thuc-google-ads': {
            'title': 'Google Ads chuyên sâu: Chinh phục Performance Max',
            'content': 'Performance Max đang dần thay thế các phương thức đặt thầu thủ công trên Google.',
            'full_text': '<p>Google Ads không còn chỉ là công cụ tìm kiếm đơn thuần. Với sự ra đời của Performance Max, quảng cáo của bạn sẽ xuất hiện trên toàn bộ hệ sinh thái của Google: Search, YouTube, Display, Gmail và Maps.</p><h2>Smart Bidding: Đặt thầu bằng trí tuệ nhân tạo</h2><p>Việc đặt thầu thủ công đã trở nên lỗi thời. Hệ thống của Google có thể dự đoán khả năng mua hàng của một người dùng ngay tại thời điểm họ tìm kiếm để điều chỉnh giá thầu tối ưu nhất.</p><h3>Tối ưu hóa trang đích (LPO)</h3><p>Quảng cáo tốt là chưa đủ, trang đích của bạn phải đạt điểm chất lượng cao và tốc độ tải trang dưới 1 giây để không lãng phí ngân sách.</p>',
            'category': 'Kiến thức',
            'author': 'Lê Văn C',
            'image': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1600&q=80'
        },
        'kien-thuc-zalo-ads': {
            'title': 'Zalo Ads: Kênh tiếp cận khách hàng Việt hiệu quả nhất',
            'content': 'Với hơn 70 triệu người dùng, Zalo Ads là mảnh đất màu mỡ cho doanh nghiệp Việt.',
            'full_text': '<p>Zalo hiện là ứng dụng nhắn tin quốc dân tại Việt Nam. Quảng cáo trên Zalo giúp bạn tiếp cận trực tiếp vào danh bạ và nhật ký của người dùng một cách tự nhiên nhất.</p><h2>Quảng cáo Form: Thu thập Lead chất lượng</h2><p>Zalo Form là công cụ tuyệt vời cho các ngành Bất động sản, Giáo dục và Tài chính. Người dùng có thể để lại thông tin chỉ với một cú chạm mà không cần nhập liệu thủ công.</p><h3>Nhắm mục tiêu theo khu vực địa lý</h3><p>Khả năng quét vị trí chính xác đến từng con đường giúp các cửa hàng địa phương tối ưu hóa chi phí quảng cáo đến khách hàng xung quanh một cách hiệu quả.</p>',
            'category': 'Kiến thức',
            'author': 'Phạm Văn D',
            'image': 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1600&q=80'
        },
        'kien-thuc-tiktok-ads': {
            'title': 'TikTok Ads: Chinh phục khách hàng qua video ngắn',
            'content': 'Biến nội dung giải trí thành cỗ máy bán hàng tự động trên TikTok.',
            'full_text': '<p>TikTok đã trở thành nền tảng có tốc độ phát triển nhanh nhất lịch sử. Tại đây, ranh giới giữa giải trí và mua sắm (Shoppertainment) đã hoàn toàn bị xóa nhòa.</p><h2>Sức mạnh của TikTok Shop Ads</h2><p>Việc kết hợp giữa livestream, video ngắn và giỏ hàng trực tiếp giúp hành trình mua hàng rút ngắn đáng kể. Thuật toán của TikTok có khả năng "thôi miên" người dùng bằng những nội dung đúng sở thích.</p><h3>Chiến lược "Don\'t Make Ads, Make TikToks"</h3><p>Đừng cố gắng tạo ra những mẫu quảng cáo bóng bẩy. Những nội dung chân thực, gần gũi và bắt trend mới là thứ giúp bạn cháy hàng trên nền tảng này.</p>',
            'category': 'Chiến thuật',
            'author': 'Hoàng Văn E',
            'image': 'https://images.unsplash.com/photo-1611605698335-8b1569810432?w=1600&q=80'
        }
    }

    # Lấy dữ liệu theo slug, nếu không có thì lấy bài mặc định
    post_data = blogs.get(slug, {
        'title': 'Bí mật chạy quảng cáo ra trăm đơn mỗi ngày',
        'content': 'Đây là nội dung chi tiết của bài viết được hiển thị khi click từ menu hoặc trang chủ.',
        'full_text': '<p>Nội dung mặc định.</p>',
        'category': 'Chung',
        'author': 'Admin',
        'image': 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1600&q=80'
    })

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
