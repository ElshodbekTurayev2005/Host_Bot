import aiosqlite
import asyncio
import os

# Baza fayl nomi
DB_PATH = "reports.db"


async def init_db():
    """Ma'lumotlar bazasini yaratish yoki tuzatish"""

    print(f"🔧 Ma'lumotlar bazasi tekshirilmoqda: {DB_PATH}")

    async with aiosqlite.connect(DB_PATH) as db:
        # Users jadvalini yaratish
        await db.execute('''
                         CREATE TABLE IF NOT EXISTS users
                         (
                             user_id
                             INTEGER
                             PRIMARY
                             KEY,
                             fullname
                             TEXT
                             NOT
                             NULL,
                             age
                             INTEGER
                             NOT
                             NULL,
                             role
                             TEXT
                             NOT
                             NULL,
                             phone
                             TEXT
                             NOT
                             NULL,
                             registered_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP,
                             last_login
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP
                         )
                         ''')
        print("✅ Users jadvali tayyor")

        # Reports jadvalini yaratish (barcha ustunlar bilan)
        await db.execute('''
                         CREATE TABLE IF NOT EXISTS reports
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             user_id
                             INTEGER
                             NOT
                             NULL,
                             fullname
                             TEXT
                             NOT
                             NULL,
                             age
                             INTEGER,
                             role
                             TEXT,
                             phone
                             TEXT,
                             anonymous
                             BOOLEAN
                             DEFAULT
                             0,
                             message
                             TEXT
                             NOT
                             NULL,
                             file_path
                             TEXT,
                             file_type
                             TEXT,
                             created_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP,
                             status
                             TEXT
                             DEFAULT
                             'new',
                             admin_reply
                             TEXT,
                             FOREIGN
                             KEY
                         (
                             user_id
                         ) REFERENCES users
                         (
                             user_id
                         )
                             )
                         ''')
        print("✅ Reports jadvali tayyor")

        await db.commit()
        print(f"✅ Ma'lumotlar bazasi muvaffaqiyatli yaratildi: {DB_PATH}")

        # Jadval strukturasini ko'rsatish
        print("\n📋 REPORTS JADVALI USTUNLARI:")
        cursor = await db.execute("PRAGMA table_info(reports)")
        columns = await cursor.fetchall()
        for col in columns:
            print(f"   • {col[1]:15} - {col[2]:10} {'(NULL ruxsat)' if col[3] == 0 else '(NOT NULL)'}")

        print("\n👥 USERS JADVALI USTUNLARI:")
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        for col in columns:
            print(f"   • {col[1]:15} - {col[2]:10} {'(NULL ruxsat)' if col[3] == 0 else '(NOT NULL)'}")

        # Statistika
        cursor = await db.execute("SELECT COUNT(*) FROM reports")
        reports_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM users")
        users_count = (await cursor.fetchone())[0]

        print(f"\n📊 STATISTIKA:")
        print(f"   • Foydalanuvchilar: {users_count}")
        print(f"   • Murojaatlar: {reports_count}")


async def check_and_fix_columns():
    """Mavjud jadvalga yo'q ustunlarni qo'shish"""

    async with aiosqlite.connect(DB_PATH) as db:
        # Reports jadvalidagi ustunlarni tekshirish
        cursor = await db.execute("PRAGMA table_info(reports)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        # Kerakli ustunlar ro'yxati
        required_columns = {
            'user_id': 'INTEGER NOT NULL',
            'fullname': 'TEXT NOT NULL',
            'age': 'INTEGER',
            'role': 'TEXT',
            'phone': 'TEXT',
            'anonymous': 'BOOLEAN DEFAULT 0',
            'message': 'TEXT NOT NULL',
            'file_path': 'TEXT',
            'file_type': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'status': 'TEXT DEFAULT "new"',
            'admin_reply': 'TEXT'
        }

        # Yo'q ustunlarni qo'shish
        for col_name, col_type in required_columns.items():
            if col_name not in column_names:
                try:
                    await db.execute(f'ALTER TABLE reports ADD COLUMN {col_name} {col_type}')
                    print(f"✅ '{col_name}' ustuni qo'shildi")
                except Exception as e:
                    print(f"⚠️  '{col_name}' ustunini qo'shib bo'lmadi: {e}")

        await db.commit()


async def reset_database():
    """Ma'lumotlar bazasini to'liq qayta yaratish"""

    if os.path.exists(DB_PATH):
        backup_name = f"{DB_PATH}.backup"
        if os.path.exists(backup_name):
            os.remove(backup_name)
        os.rename(DB_PATH, backup_name)
        print(f"📦 Eski baza backup qilindi: {backup_name}")

    await init_db()


if __name__ == "__main__":
    print("=" * 50)
    print("🛠️  MA'LUMOTLAR BAZASI TUZATISH VOSITASI")
    print("=" * 50)
    print("\n1 - Bazani tekshirish va tuzatish (xavfsiz)")
    print("2 - Yo'q ustunlarni qo'shish")
    print("3 - Bazani to'liq qayta yaratish (backup bilan)")
    print("4 - Faqat struktura ko'rsatish")

    choice = input("\nTanlang (1-4): ").strip()

    if choice == "1":
        asyncio.run(init_db())
    elif choice == "2":
        asyncio.run(check_and_fix_columns())
        print("\n✅ Ustunlar qo'shildi!")
        asyncio.run(init_db())
    elif choice == "3":
        confirm = input("⚠️  Hamma ma'lumotlar o'chiriladi! Davom etish? (yes/no): ")
        if confirm.lower() in ['yes', 'y', 'ha']:
            asyncio.run(reset_database())
        else:
            print("❌ Bekor qilindi")
    elif choice == "4":
        asyncio.run(init_db())
    else:
        print("❌ Noto'g'ri tanlov!")

    print("\n" + "=" * 50)
    print("✅ Tayyor! Endi botni ishga tushiring:")
    print("   python bot.py")
    print("=" * 50)