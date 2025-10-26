import aiosqlite
from datetime import datetime
import logging
import os
from config import DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Database va jadvallarni yaratish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Users jadvali
                await db.execute('''
                                 CREATE TABLE IF NOT EXISTS users
                                 (
                                     user_id
                                     INTEGER
                                     PRIMARY
                                     KEY,
                                     username
                                     TEXT,
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

                # Reports jadvali - soddalashtirilgan
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
                                     TEXT,
                                     age
                                     INTEGER,
                                     phone
                                     TEXT,
                                     role
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
                                     status
                                     TEXT
                                     DEFAULT
                                     'new',
                                     created_at
                                     TIMESTAMP
                                     DEFAULT
                                     CURRENT_TIMESTAMP,
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

                await db.commit()
                logger.info("✅ Database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def add_user(self, user_id, fullname, age, role, phone, username=None):
        """Yangi foydalanuvchi qo'shish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, fullname, age, role, phone, last_login)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, username, fullname, age, role, phone))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"❌ User qo'shishda xatolik: {e}")
            return False

    async def get_user(self, user_id):
        """Foydalanuvchi ma'lumotlarini olish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT * FROM users WHERE user_id = ?',
                    (user_id,)
                )
                user = await cursor.fetchone()
                return user
        except Exception as e:
            logger.error(f"❌ User olishda xatolik: {e}")
            return None

    async def update_user(self, user_id, **kwargs):
        """Foydalanuvchi ma'lumotlarini yangilash"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if kwargs:
                    fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
                    values = list(kwargs.values()) + [user_id]
                    await db.execute(
                        f'UPDATE users SET {fields}, last_login = CURRENT_TIMESTAMP WHERE user_id = ?',
                        values
                    )
                    await db.commit()
                    return True
        except Exception as e:
            logger.error(f"❌ User yangilashda xatolik: {e}")
            return False

    async def add_report(self, user_id, fullname, age, phone, role, anonymous, message, file_path=None, file_type=None):
        """Yangi murojaat qo'shish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                                          INSERT INTO reports
                                          (user_id, fullname, age, phone, role, anonymous, message, file_path,
                                           file_type)
                                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                          ''', (user_id, fullname, age, phone, role, anonymous, message, file_path,
                                                file_type))

                await db.commit()
                report_id = cursor.lastrowid
                logger.info(f"✅ Report #{report_id} qo'shildi")
                return report_id
        except Exception as e:
            logger.error(f"❌ Report qo'shishda xatolik: {e}")
            return None

    async def get_report(self, report_id):
        """Murojaat ma'lumotlarini olish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT * FROM reports WHERE id = ?',
                    (report_id,)
                )
                report = await cursor.fetchone()
                return report
        except Exception as e:
            logger.error(f"❌ Report olishda xatolik: {e}")
            return None

    async def get_user_reports(self, user_id, limit=50):
        """Foydalanuvchi murojaatlarini olish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                                          SELECT *
                                          FROM reports
                                          WHERE user_id = ?
                                          ORDER BY created_at DESC LIMIT ?
                                          ''', (user_id, limit))
                reports = await cursor.fetchall()
                return reports
        except Exception as e:
            logger.error(f"❌ User reports olishda xatolik: {e}")
            return []

    async def get_all_reports(self, status=None, limit=50):
        """Barcha murojaatlarni olish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if status:
                    cursor = await db.execute('''
                                              SELECT *
                                              FROM reports
                                              WHERE status = ?
                                              ORDER BY created_at DESC LIMIT ?
                                              ''', (status, limit))
                else:
                    cursor = await db.execute('''
                                              SELECT *
                                              FROM reports
                                              ORDER BY created_at DESC LIMIT ?
                                              ''', (limit,))

                reports = await cursor.fetchall()
                return reports
        except Exception as e:
            logger.error(f"❌ All reports olishda xatolik: {e}")
            return []

    async def update_report_status(self, report_id, status):
        """Murojaat statusini yangilash"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE reports SET status = ? WHERE id = ?',
                    (status, report_id)
                )
                await db.commit()
                logger.info(f"✅ Report #{report_id} statusi {status} ga o'zgartirildi")
                return True
        except Exception as e:
            logger.error(f"❌ Report status yangilashda xatolik: {e}")
            return False

    async def add_admin_reply(self, report_id, reply_text):
        """Admin javobini qo'shish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE reports SET admin_reply = ? WHERE id = ?',
                    (reply_text, report_id)
                )
                await db.commit()
                logger.info(f"✅ Report #{report_id} ga javob qo'shildi")
                return True
        except Exception as e:
            logger.error(f"❌ Admin reply qo'shishda xatolik: {e}")
            return False

    async def delete_report(self, report_id):
        """Murojaatni o'chirish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Avval faylni o'chirish
                cursor = await db.execute(
                    'SELECT file_path FROM reports WHERE id = ?',
                    (report_id,)
                )
                result = await cursor.fetchone()

                if result and result[0] and os.path.exists(result[0]):
                    try:
                        os.remove(result[0])
                    except Exception as e:
                        logger.error(f"❌ Fayl o'chirishda xatolik: {e}")

                await db.execute('DELETE FROM reports WHERE id = ?', (report_id,))
                await db.commit()
                logger.info(f"✅ Report #{report_id} o'chirildi")
                return True
        except Exception as e:
            logger.error(f"❌ Report o'chirishda xatolik: {e}")
            return False

    async def get_stats(self):
        """Statistika olish"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Umumiy murojaatlar
                cursor = await db.execute('SELECT COUNT(*) FROM reports')
                total_reports = (await cursor.fetchone())[0]

                # Foydalanuvchilar soni
                cursor = await db.execute('SELECT COUNT(*) FROM users')
                total_users = (await cursor.fetchone())[0]

                # Status bo'yicha
                cursor = await db.execute("SELECT COUNT(*) FROM reports WHERE status = 'new'")
                new_reports = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(*) FROM reports WHERE status = 'processing'")
                processing_reports = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(*) FROM reports WHERE status = 'resolved'")
                resolved_reports = (await cursor.fetchone())[0]

                # Anonim murojaatlar
                cursor = await db.execute("SELECT COUNT(*) FROM reports WHERE anonymous = 1")
                anonymous_reports = (await cursor.fetchone())[0]

                return {
                    'total_reports': total_reports,
                    'total_users': total_users,
                    'new_reports': new_reports,
                    'processing_reports': processing_reports,
                    'resolved_reports': resolved_reports,
                    'anonymous_reports': anonymous_reports
                }
        except Exception as e:
            logger.error(f"❌ Statistika olishda xatolik: {e}")
            return {}

    async def check_database_structure(self):
        """Database strukturasi tekshiruvi"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Users jadvali ustunlari
                cursor = await db.execute("PRAGMA table_info(users)")
                user_columns = await cursor.fetchall()
                logger.info("👥 Users jadvali ustunlari:")
                for col in user_columns:
                    logger.info(f"   • {col[1]} ({col[2]})")

                # Reports jadvali ustunlari
                cursor = await db.execute("PRAGMA table_info(reports)")
                report_columns = await cursor.fetchall()
                logger.info("📋 Reports jadvali ustunlari:")
                for col in report_columns:
                    logger.info(f"   • {col[1]} ({col[2]})")

                return True
        except Exception as e:
            logger.error(f"❌ Database structure tekshirishda xatolik: {e}")
            return False


# Global database instance
db = Database()


async def init_database():
    """Database ni ishga tushirish"""
    await db.init_db()
    await db.check_database_structure()


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_database())