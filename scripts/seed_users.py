from app import create_app
from app.models.base import DBModel
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    pw_hash = generate_password_hash('admin123')
    
    # Insert admin if not exists
    admin_exists = DBModel.fetch_one("SELECT id FROM users WHERE username = 'admin'")
    if not admin_exists:
        DBModel.execute("INSERT INTO users (username, password, role) VALUES ('admin', %s, 'admin')", (pw_hash,))
        print("Admin user created (admin / admin123)")
    else:
        DBModel.execute("UPDATE users SET password = %s WHERE username = 'admin'", (pw_hash,))
        print("Admin user updated (admin / admin123)")

    # Insert marketer if not exists
    marketer_exists = DBModel.fetch_one("SELECT id FROM users WHERE username = 'marketer1'")
    if not marketer_exists:
        DBModel.execute("INSERT INTO users (username, password, role) VALUES ('marketer1', %s, 'marketer')", (pw_hash,))
        print("Marketer user created (marketer1 / admin123)")
    else:
        DBModel.execute("UPDATE users SET password = %s WHERE username = 'marketer1'", (pw_hash,))
        print("Marketer user updated (marketer1 / admin123)")
