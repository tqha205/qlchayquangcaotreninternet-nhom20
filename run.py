from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == '__main__':
    print("ADS Manager System running at http://localhost:5001")
    # use_reloader=False: tránh lỗi WinError 10048 (port bị bind 2 lần khi reload)
    # async_mode='threading': không cần eventlet, ổn định hơn trên Windows
    socketio.run(app, debug=True, port=5001,
                 use_reloader=False, allow_unsafe_werkzeug=True)
