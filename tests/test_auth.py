"""
tests/test_auth.py
==================
Unit tests cho Auth Controller (đăng nhập, đăng ký, logout).
"""

import pytest


class TestLoginRoute:
    """Kiểm tra route POST /auth/login"""

    def test_login_missing_fields_returns_400(self, client):
        """Thiếu trường dữ liệu → 400 Bad Request"""
        resp = client.post('/auth/login', json={})
        assert resp.status_code == 400

    def test_login_short_username_returns_400(self, client):
        """Username < 3 ký tự → 400"""
        resp = client.post('/auth/login', json={'username': 'ab', 'password': 'abc123'})
        assert resp.status_code == 400

    def test_login_short_password_returns_400(self, client):
        """Password < 6 ký tự → 400"""
        resp = client.post('/auth/login', json={'username': 'admin', 'password': '123'})
        assert resp.status_code == 400

    def test_login_wrong_credentials_returns_401(self, client):
        """Sai tài khoản/mật khẩu → 401 Unauthorized"""
        resp = client.post('/auth/login', json={'username': 'nonexistent', 'password': 'wrongpassword'})
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['success'] is False

    def test_login_returns_json(self, client):
        """Response phải là JSON"""
        resp = client.post('/auth/login', json={'username': 'test', 'password': 'test123'})
        assert resp.content_type == 'application/json'


class TestRegisterRoute:
    """Kiểm tra route POST /auth/register"""

    def test_register_missing_required_fields_returns_400(self, client):
        """Thiếu full_name → 400"""
        resp = client.post('/auth/register', json={
            'username': 'newuser',
            'password': 'password123'
        })
        assert resp.status_code == 400

    def test_register_short_username_returns_400(self, client):
        """Username < 3 → 400"""
        resp = client.post('/auth/register', json={
            'username': 'ab',
            'password': 'password123',
            'full_name': 'Test User'
        })
        assert resp.status_code == 400

    def test_register_short_password_returns_400(self, client):
        """Password < 6 → 400"""
        resp = client.post('/auth/register', json={
            'username': 'newuser',
            'password': '123',
            'full_name': 'Test User'
        })
        assert resp.status_code == 400

    def test_register_invalid_email_returns_400(self, client):
        """Email không hợp lệ → 400"""
        resp = client.post('/auth/register', json={
            'username': 'newuser',
            'password': 'password123',
            'full_name': 'Test User',
            'email': 'not-an-email'
        })
        assert resp.status_code == 400


class TestLogoutRoute:
    """Kiểm tra route GET /auth/logout"""

    def test_logout_redirects(self, client):
        """Logout phải redirect (302)"""
        resp = client.get('/auth/logout')
        assert resp.status_code == 302
