"""
app/sockets.py
==============
Định nghĩa các SocketIO event handlers cho hệ thống real-time.

Kết nối từ client (JavaScript):
    const socket = io();
    socket.emit('join', { user_id: userId });
    socket.on('budget_warning', (data) => showToast(data));
    socket.on('budget_exceeded', (data) => showToast(data));
    socket.on('new_notification', (data) => updateBadge(data));
"""

import logging
from flask import request
from flask_socketio import join_room, emit

logger = logging.getLogger(__name__)


def register_socket_events(socketio):
    """Đăng ký tất cả SocketIO event handlers vào instance socketio."""

    @socketio.on('connect')
    def on_connect():
        logger.debug(f"[SocketIO] Client kết nối: {request.sid}")

    @socketio.on('disconnect')
    def on_disconnect():
        logger.debug(f"[SocketIO] Client ngắt kết nối: {request.sid}")

    @socketio.on('join')
    def on_join(data):
        """
        Client gửi event 'join' sau khi đăng nhập để tham gia phòng riêng.
        Payload: { user_id: <int> }
        """
        user_id = data.get('user_id')
        if user_id:
            room = f"user_{user_id}"
            join_room(room)
            emit('joined', {'room': room, 'status': 'ok'})
            logger.info(f"[SocketIO] User #{user_id} đã join room '{room}'")

    @socketio.on('ping_test')
    def on_ping(data):
        """Dùng để kiểm tra kết nối SocketIO có hoạt động không."""
        emit('pong_test', {'message': 'SocketIO đang hoạt động!'})
