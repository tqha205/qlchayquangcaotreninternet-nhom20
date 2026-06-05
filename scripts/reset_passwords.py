#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để reset mật khẩu người dùng mẫu sang mật khẩu đơn giản: 123456
"""

import sys
sys.path.insert(0, '.')

from app.models import UserModel

# Reset mật khẩu mặc định là '123456' cho các tài khoản mẫu
users_to_reset = [
    (1, 'admin'),
    (2, 'marketer1'),
    (3, 'client1')
]

for user_id, username in users_to_reset:
    success = UserModel.update(user_id, password='123456')
    status = "✓" if success else "✗"
    print(f"{status} Reset mật khẩu cho {username} (ID: {user_id}) → 123456")

print("\n✓ Hoàn tất! Bạn có thể đăng nhập ngay.")
