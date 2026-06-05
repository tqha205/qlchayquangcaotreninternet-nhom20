import pymysql

connection = pymysql.connect(host='localhost', user='root', password='', database='ads_manager_db')
try:
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SHOW TRIGGERS;")
        triggers = cursor.fetchall()
        with open('triggers_output.txt', 'w', encoding='utf-8') as f:
            for t in triggers:
                f.write(f"Trigger: {t['Trigger']}\n")
                f.write(f"Statement: {t['Statement']}\n")
                f.write("-" * 50 + "\n")
finally:
    connection.close()
