import sqlite3

DB_PATH = r"C:\Users\user\Desktop\bot\database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE reports ADD COLUMN user_id INTEGER")
    print("✅ 'user_id' ustuni qo‘shildi.")
except sqlite3.OperationalError:
    print("✅ 'user_id' ustuni allaqachon mavjud.")

conn.commit()
conn.close()

print("🎉 Baza strukturasini tekshirish tugadi.")
