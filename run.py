from app import create_app

app = create_app()

if __name__ == '__main__':
    # Mặc định chạy ở cổng 5000 cho toàn bộ hệ thống (Public + Admin)
    print("ADS Manager System running at http://localhost:5000")
    app.run(debug=True, port=5000)
