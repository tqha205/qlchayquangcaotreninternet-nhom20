"""
tests/test_basic.py
===================
Smoke tests cơ bản để xác nhận app khởi động đúng.
"""


def test_app_exists(app):
    """App Flask phải tồn tại."""
    assert app is not None


def test_app_is_testing(app):
    """App phải ở chế độ TESTING."""
    assert app.config['TESTING'] is True


def test_home_redirects_or_ok(client):
    """Trang chủ phải trả về 200 hoặc redirect (302)."""
    response = client.get('/')
    assert response.status_code in (200, 302)


def test_404_returns_404(client):
    """Route không tồn tại phải trả về 404."""
    response = client.get('/duong-dan-khong-ton-tai-xyz-abc')
    assert response.status_code == 404
