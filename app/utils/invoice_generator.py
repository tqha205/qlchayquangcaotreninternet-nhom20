import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register a Unicode font to support Vietnamese accents
FONT_NAME = 'Helvetica'
font_paths = [
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\tahoma.ttf",
    "C:\\Windows\\Fonts\\calibri.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
]
for path in font_paths:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont('UnicodeFont', path))
            FONT_NAME = 'UnicodeFont'
            break
        except Exception:
            pass

def generate_invoice_pdf(transaction, customer):
    """
    Sinh file PDF hóa đơn chuyên nghiệp sử dụng reportlab.
    Trả về (relative_path, absolute_path)
    """
    # 1. Setup paths
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'invoices')
    os.makedirs(uploads_dir, exist_ok=True)
    
    invoice_date = transaction.created_at or datetime.utcnow()
    date_str = invoice_date.strftime('%Y%m%d')
    invoice_number = f"INV-{date_str}-{transaction.id:04d}"
    
    filename = f"{invoice_number}.pdf"
    abs_path = os.path.join(uploads_dir, filename)
    rel_path = f"/static/uploads/invoices/{filename}"
    
    # 2. Build Document
    doc = SimpleDocTemplate(abs_path, pagesize=letter,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName=FONT_NAME,
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#4F46E5'),  # Modern indigo primary
        alignment=0, # Left-aligned
        spaceAfter=15
    )
    
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    
    meta_val_style = ParagraphStyle(
        'MetaValue',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F172A'),
        alignment=2 # Right-aligned
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading3'],
        fontName=FONT_NAME,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=10,
        spaceAfter=5
    )
    
    text_style = ParagraphStyle(
        'TextNormal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    
    bold_text_style = ParagraphStyle(
        'TextBold',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )
    
    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.white
    )
    
    # --- Title & Metadata Section ---
    header_data = [
        [
            Paragraph("HÓA ĐƠN THANH TOÁN", title_style),
            Paragraph(f"<b>Mã số hóa đơn:</b> {invoice_number}", meta_val_style)
        ],
        [
            Paragraph("Hệ thống quản lý ADS Manager", meta_label_style),
            Paragraph(f"<b>Ngày lập:</b> {invoice_date.strftime('%d/%m/%Y %H:%M')}", meta_val_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[260, 260])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 20))
    
    # Divider line
    divider = Table([['']], colWidths=[520])
    divider.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(divider)
    
    # --- Parties Info Section (Sender & Receiver) ---
    info_data = [
        [
            Paragraph("ĐƠN VỊ CUNG CẤP", header_style),
            Paragraph("THÔNG TIN KHÁCH HÀNG", header_style)
        ],
        [
            Paragraph("<b>Công ty:</b> ADS Manager JSC<br/>"
                      "<b>Hotline:</b> 1900 xxxx<br/>"
                      "<b>Email:</b> support@adsmanager.com<br/>"
                      "<b>Website:</b> https://adsmanager.com", text_style),
            Paragraph(f"<b>Khách hàng:</b> {customer.name or '—'}<br/>"
                      f"<b>Doanh nghiệp:</b> {customer.company or 'Cá nhân'}<br/>"
                      f"<b>Email:</b> {customer.email or '—'}<br/>"
                      f"<b>Số điện thoại:</b> {customer.phone or '—'}", text_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[260, 260])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # --- Transaction details ---
    story.append(Paragraph("CHI TIẾT THANH TOÁN", header_style))
    story.append(Spacer(1, 5))
    
    amount_val = float(transaction.amount or 0)
    tx_type = "Nạp tiền vào tài khoản (Deposit)" if transaction.type == 'deposit' else transaction.type
    
    table_data = [
        [
            Paragraph("<b>Nội dung thanh toán</b>", th_style),
            Paragraph("<b>Phương thức</b>", th_style),
            Paragraph("<b>Mã giao dịch</b>", th_style),
            Paragraph("<b>Tổng tiền (VNĐ)</b>", th_style)
        ],
        [
            Paragraph(transaction.description or tx_type, text_style),
            Paragraph(transaction.payment_method or "Chuyển khoản ngân hàng", text_style),
            Paragraph(str(transaction.id), text_style),
            Paragraph(f"<b>{amount_val:,.0f} đ</b>", bold_text_style)
        ]
    ]
    
    tx_table = Table(table_data, colWidths=[200, 110, 90, 120])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4F46E5')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(tx_table)
    story.append(Spacer(1, 40))
    
    # --- Footer Note ---
    footer_style = ParagraphStyle(
        'FooterNote',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#94A3B8'),
        alignment=1, # Centered
        spaceBefore=20
    )
    story.append(Paragraph("Cảm ơn quý khách đã tin tưởng và sử dụng dịch vụ của chúng tôi!<br/>"
                           "Mọi thắc mắc xin vui lòng liên hệ bộ phận CSKH để được hỗ trợ giải quyết.", footer_style))
    
    doc.build(story)
    return rel_path, abs_path
