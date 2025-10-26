import aiosqlite
import asyncio

DB_PATH = "database.db"


async def add_missing_columns():
    """Yo'q ustunlarni qo'shish"""

    async with aiosqlite.connect(DB_PATH) as db:
        print("🔧 Ustunlar tekshirilmoqda...\n")

        # Reports jadvali ustunlarini tekshirish
        cursor = await db.execute("PRAGMA table_info(reports)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        print("📋 Mavjud ustunlar:", ", ".join(column_names))
        print()

        # admin_reply ustunini qo'shish
        if 'admin_reply' not in column_names:
            try:
                await db.execute('ALTER TABLE reports ADD COLUMN admin_reply TEXT')
                await db.commit()
                print("✅ 'admin_reply' ustuni qo'shildi")
            except Exception as e:
                print(f"⚠️  admin_reply: {e}")
        else:
            print("✅ 'admin_reply' ustuni mavjud")

        # Users jadvaliga role qo'shish
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        user_column_names = [col[1] for col in columns]

        if 'role' not in user_column_names:
            try:
                await db.execute('ALTER TABLE users ADD COLUMN role TEXT')
                await db.commit()
                print("✅ 'role' ustuni users jadvaliga qo'shildi")
            except Exception as e:
                print(f"⚠️  role: {e}")
        else:
            print("✅ 'role' ustuni mavjud")

        # Yangilangan strukturani ko'rsatish
        print("\n" + "=" * 50)
        print("📋 REPORTS JADVALI (yangilangan):")
        cursor = await db.execute("PRAGMA table_info(reports)")
        columns = await cursor.fetchall()
        for col in columns:
            print(f"   • {col[1]:15} - {col[2]}")

        print("\n👥 USERS JADVALI (yangilangan):")
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        for col in columns:
            print(f"   • {col[1]:15} - {col[2]}")

        print("=" * 50)


if __name__ == "__main__":
    print("🛠️  USTUNLAR QO'SHISH SKRIPTI\n")
    asyncio.run(add_missing_columns())
    print("\n✅ Tayyor! Endi botni ishga tushiring:")
    print("   python bot.py")