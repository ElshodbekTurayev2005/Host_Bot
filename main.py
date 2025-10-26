import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
)
import aiosqlite
import os
import openpyxl

# ==================== CONFIG DAN IMPORT ====================
from config import BOT_TOKEN, ADMIN_ID, DB_PATH, UPLOADS_DIR

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== BOT VA DISPATCHER ====================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

logger.info("✅ Bot va Dispatcher ishga tayyor.")

# ==================== DATABASE FUNCTIONS ====================
async def init_db():
    """Database va jadvallarni yaratish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Users jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    fullname TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Reports jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                                                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                       user_id INTEGER,
                                                       fullname TEXT NOT NULL,
                                                       age INTEGER NOT NULL,
                                                       role TEXT NOT NULL,
                                                       phone TEXT NOT NULL,
                                                       anonymous BOOLEAN,
                                                       message TEXT NOT NULL,
                                                       file_path TEXT,
                                                       file_type TEXT,
                                                       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                                       status TEXT DEFAULT 'new',
                                                       admin_reply TEXT,
                                                       FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            await db.commit()
            logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

async def add_user(user_id, fullname, age, role, phone):
    """Yangi foydalanuvchi qo'shish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, fullname, age, role, phone, last_login)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, fullname, age, role, phone))
            await db.commit()
            logger.info(f"✅ User {user_id} added with fullname: {fullname}")
            return True
    except Exception as e:
        logger.error(f"❌ User qo'shishda xatolik: {e}")
        return False

async def get_user(user_id):
    """Foydalanuvchi ma'lumotlarini olish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                'SELECT * FROM users WHERE user_id = ?',
                (user_id,)
            )
            user = await cursor.fetchone()
            return user
    except Exception as e:
        logger.error(f"❌ User olishda xatolik: {e}")
        return None

async def update_user(user_id, **kwargs):
    """Foydalanuvchi ma'lumotlarini yangilash"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
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

async def save_report(data):
    """Yangi murojaat saqlash"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            user_id = data.get('user_id')
            # Foydalanuvchi ma'lumotlarini olish
            user = await get_user(user_id)
            if not user:
                logger.error(f"❌ User {user_id} topilmadi")
                return None

            fullname = user[1]  # users jadvalidan ismni olish
            age = data.get('age', '')
            role = data.get('role', '')
            phone = data.get('phone', '')
            message = data.get('message', '')

            # Ma'lumotlarni tekshirish
            if not all([fullname, age, role, phone, message]):
                logger.error(f"❌ Ma'lumotlar to'liq emas: fullname={fullname}, age={age}, role={role}, phone={phone}, message={message}")
                return None

            # Foydalanuvchi ma'lumotlarini yangilash
            await db.execute('''
                INSERT OR REPLACE INTO users (user_id, fullname, age, role, phone, last_login)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, fullname, age, role, phone))

            # Murojaatni saqlash
            cursor = await db.execute('''
                INSERT INTO reports (user_id, fullname, age, role, phone, anonymous, message,
                                   file_path, file_type, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'new')
            ''', (
                user_id, fullname, age, role, phone,
                data.get('anonymous', False), message,
                data.get('file_path'), data.get('file_type')
            ))
            await db.commit()

            cursor = await db.execute("SELECT last_insert_rowid()")
            report_id = (await cursor.fetchone())[0]
            logger.info(f"✅ Report #{report_id} saved for user {user_id} with fullname: {fullname}")
            return report_id
    except Exception as e:
        logger.error(f"❌ Report saqlashda xatolik: {e}")
        return None

async def get_user_reports(user_id):
    """Foydalanuvchi murojaatlarini olish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT * FROM reports 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            reports = await cursor.fetchall()
            return reports
    except Exception as e:
        logger.error(f"❌ User reports olishda xatolik: {e}")
        return []

async def get_report(report_id):
    """Murojaat ma'lumotlarini olish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                'SELECT * FROM reports WHERE id = ?',
                (report_id,)
            )
            report = await cursor.fetchone()
            return report
    except Exception as e:
        logger.error(f"❌ Report olishda xatolik: {e}")
        return None

async def get_all_reports(status=None, limit=50):
    """Barcha murojaatlarni olish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            if status:
                cursor = await db.execute('''
                    SELECT id, created_at, status, fullname 
                    FROM reports 
                    WHERE status = ? 
                    ORDER BY created_at DESC LIMIT ?
                ''', (status, limit))
            else:
                cursor = await db.execute('''
                    SELECT id, created_at, status, fullname 
                    FROM reports 
                    ORDER BY created_at DESC LIMIT ?
                ''', (limit,))

            reports = await cursor.fetchall()
            return reports
    except Exception as e:
        logger.error(f"❌ All reports olishda xatolik: {e}")
        return []

async def get_full_reports(status=None):
    """Barcha murojaatlarni to'liq ma'lumot bilan olish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            if status:
                cursor = await db.execute('''
                    SELECT * FROM reports 
                    WHERE status = ? 
                    ORDER BY created_at DESC
                ''', (status,))
            else:
                cursor = await db.execute('''
                    SELECT * FROM reports 
                    ORDER BY created_at DESC
                ''')

            reports = await cursor.fetchall()
            return reports
    except Exception as e:
        logger.error(f"❌ Full reports olishda xatolik: {e}")
        return []

async def update_report_status(report_id, status):
    """Murojaat statusini yangilash"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
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

async def add_admin_reply(report_id, reply_text):
    """Admin javobini qo'shish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
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

async def delete_report(report_id):
    """Murojaatni o'chirish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
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

async def get_stats():
    """Statistika olish"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
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

# ==================== UTILS ====================
async def save_file_from_message(message: Message):
    """Faylni saqlash"""
    file_path = None
    file_type = None

    try:
        if message.photo:
            file = await bot.get_file(message.photo[-1].file_id)
            file_type = "photo"
            ext = "jpg"
        elif message.document:
            file = await bot.get_file(message.document.file_id)
            file_type = "document"
            ext = message.document.file_name.split('.')[-1] if message.document.file_name else "file"
        elif message.video:
            file = await bot.get_file(message.video.file_id)
            file_type = "video"
            ext = "mp4"
        else:
            return None, None

        if file:
            file_name = f"{file_type}_{message.from_user.id}_{int(datetime.now().timestamp())}.{ext}"
            file_path = os.path.join(UPLOADS_DIR, file_name)
            await bot.download_file(file.file_path, file_path)
            return file_path, file_type
    except Exception as e:
        logger.error(f"❌ Fayl saqlashda xatolik: {e}")

    return None, None

async def send_to_admin(report_id):
    """Adminga murojaat yuborish"""
    report = await get_report(report_id)
    if not report:
        logger.error(f"❌ Report #{report_id} topilmadi")
        return

    # Report ma'lumotlari
    rid = report[0]
    user_id = report[1]
    age = report[3]
    role = report[4]
    phone = report[5]
    anonymous = report[6]
    message = report[7]
    file_path = report[8]
    file_type = report[9]
    date = report[10]
    status = report[11]

    # Foydalanuvchi ma'lumotlarini olish
    user = await get_user(user_id)
    fullname = user[1] if user else "Noma'lum"

    admin_text = (
        f"🆕 <b>YANGI MUROJAAT!</b>\n"
        f"{'=' * 30}\n\n"
        f"📋 <b>ID:</b> <code>#{rid}</code>\n"
        f"👤 <b>Ism:</b> {fullname}\n"
        f"🎂 <b>Yosh:</b> {age}\n"
        f"👔 <b>Rol:</b> {role}\n"
        f"📞 <b>Telefon:</b> <code>{phone}</code>\n"
        f"🔐 <b>Tur:</b> {'🔒 Anonim' if anonymous else '👁 Ochiq'}\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"📅 <b>Sana:</b> {date}\n\n"
        f"📝 <b>Murojaat matni:</b>\n{message}\n\n"
        f"📎 <b>Dalil:</b> {"✅ Mavjud' if file_path else '❌ Yo`q"}\n"
        f"{'=' * 30}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👀 Ko'rish", callback_data=f"admin_view_{rid}"),
            InlineKeyboardButton(text="💬 Javob", callback_data=f"reply_{rid}")
        ],
        [
            InlineKeyboardButton(text="⏳ Ko'rilmoqda", callback_data=f"status_processing_{rid}"),
            InlineKeyboardButton(text="✅ Hal qilindi", callback_data=f"status_resolved_{rid}")
        ],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_confirm_{rid}")]
    ])

    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode='HTML', reply_markup=kb)
        logger.info(f"✅ Notification sent for report #{rid} with fullname: {fullname}")
    except Exception as e:
        logger.error(f"❌ Adminga xabar yuborishda xatolik: {e}")

    # Faylni yuborish
    if file_path and os.path.exists(file_path):
        try:
            file = FSInputFile(file_path)
            caption = f"📎 Murojaat #{rid} dalili"

            if file_type == "photo":
                await bot.send_photo(ADMIN_ID, file, caption=caption)
            elif file_type == "video":
                await bot.send_video(ADMIN_ID, file, caption=caption)
            elif file_type == "document":
                await bot.send_document(ADMIN_ID, file, caption=caption)
        except Exception as e:
            logger.error(f"❌ Fayl yuborishda xatolik: {e}")

# ==================== FSM STATES ====================
class UserStates(StatesGroup):
    waiting_fullname = State()
    waiting_age = State()
    waiting_role = State()
    waiting_phone = State()
    waiting_anonymous = State()
    waiting_message = State()
    waiting_file = State()

class AdminStates(StatesGroup):
    waiting_response = State()

# ==================== START HANDLER ====================
@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()

    if message.from_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎛 Admin Panel", callback_data="admin_panel")]
        ])
        await message.answer(
            "👑 <b>Admin menyusi</b>\n\n"
            "Siz admin sifatida tizimga kirdingiz.",
            parse_mode='HTML',
            reply_markup=kb
        )
        return

    user = await get_user(message.from_user.id)

    if not user:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", callback_data="register_start")]
        ])
        await message.answer(
            "🖐 <b>Assalomu alaykum!</b>\n\n"
            "Murojaatingizni qabul qilishga tayyormiz. Imkon qadar aniq dalillar va faktlarga "
            "tayanishingizni so'raymiz. Sizning xabaringiz to'g'ridan-to'g'ri vrachlarning kasbiy "
            "malakasini oshirish markazi rahbariyati kuzatuvida.\n\n"
            "Eslatib o'tamiz. Har bir murojaat, murojaatchining shaxsi qonunda belgilangan tartibda "
            "mutlaqo sir saqlangan holda o'rganiladi va o'rganish natijalari bo'yicha hujjatlar "
            "zarur hollarda qonuniy baho berish uchun tegishli vakolatli huquqni muhofaza qiluvchi "
            "organlarga taqdim etiladi.\n\n"
            "❗️ Ma'lumot o'rnida, anonim (muallif ismi, sharifi, yashash joyi ko'rsatilmagan yoki "
            "soxta bo'lgan) murojaatlar O'zbekiston Respublikasining \"Jismoniy va yuridik shaxslarning "
            "murojaatlari to'g'risida\" Qonuniga asosan ko'rib chiqilmaydi!",
            parse_mode='HTML',
            reply_markup=kb
        )
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📩 Yangi murojaat", callback_data="new_report")],
            [InlineKeyboardButton(text="📋 Murojaatlarim", callback_data="my_reports")],
            [InlineKeyboardButton(text="👤 Profil", callback_data="profile")],
        ])
        await message.answer(
            f"🖐 <b>Assalomu alaykum, {user[1]}!</b>\n\n"
            f"👔 <b>Rol:</b> {user[3]}\n"
            f"📞 <b>Telefon:</b> {user[4]}\n\n"
            "Quyidagi bo'limlardan birini tanlang:",
            parse_mode='HTML',
            reply_markup=kb
        )

# ==================== RO'YXATDAN O'TISH ====================
@dp.callback_query(F.data == "register_start")
async def register_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserStates.waiting_fullname)

    await callback.message.edit_text(
        "👤 <b>Ro'yxatdan o'tish</b>\n\n"
        "Iltimos, to'liq ismingizni kiriting:\n\n"
        "<i>Masalan: Aliyev Ali Vali o'g'li</i>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor qilish ❌", callback_data="cancel")]
        ])
    )

@dp.message(UserStates.waiting_fullname)
async def process_fullname(message: Message, state: FSMContext):
    fullname = message.text.strip()

    if len(fullname) < 3:
        await message.answer("❌ Ism juda qisqa. Iltimos, to'liq ismingizni kiriting:")
        return

    data = await state.get_data()
    if 'editing' in data and data['editing'] == 'name':
        success = await update_user(message.from_user.id, fullname=fullname)
        if success:
            await message.answer("✅ Ism muvaffaqiyatli o'zgartirildi!")
            await state.clear()
            user = await get_user(message.from_user.id)
            profile_text = (
                f"👤 <b>SHAXSIY KABINET</b>\n"
                f"{'=' * 30}\n\n"
                f"📝 <b>Ism:</b> {user[1]}\n"
                f"🎂 <b>Yosh:</b> {user[2]}\n"
                f"👔 <b>Rol:</b> {user[3]}\n"
                f"📞 <b>Telefon:</b> {user[4]}\n"
                f"📅 <b>Ro'yxatdan o'tgan:</b> {user[5][:10] if user[5] else 'Noma\'lum'}\n\n"
                f"📊 <b>STATISTIKA:</b>\n"
                f"• Jami murojaatlar: {len(await get_user_reports(message.from_user.id))}\n"
                f"• Yangi: {sum(1 for r in await get_user_reports(message.from_user.id) if r[11] == 'new')}\n"
                f"• Hal qilingan: {sum(1 for r in await get_user_reports(message.from_user.id) if r[11] == 'resolved')}\n"
                f"{'=' * 30}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Profilni tahrirlash", callback_data="edit_profile")],
                [InlineKeyboardButton(text="📋 Murojaatlarim", callback_data="my_reports")],
                [InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="main_menu")]
            ])
            await message.answer(profile_text, parse_mode='HTML', reply_markup=kb)
        else:
            await message.answer("❌ Xatolik!")
    else:
        await state.update_data(fullname=fullname)
        await state.set_state(UserStates.waiting_age)

        await message.answer(
            "🎂 <b>Yoshingizni kiriting:</b>\n\n"
            "<i>Masalan: 25</i>",
            parse_mode='HTML'
        )

@dp.message(UserStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text.strip())
        if age < 14 or age > 100:
            raise ValueError
    except:
        await message.answer("❌ Noto'g'ri yosh! 14-100 oralig'ida kiriting:")
        return

    data = await state.get_data()
    if 'editing' in data and data['editing'] == 'age':
        success = await update_user(message.from_user.id, age=age)
        if success:
            await message.answer("✅ Yosh muvaffaqiyatli o'zgartirildi!")
            await state.clear()
            user = await get_user(message.from_user.id)
            profile_text = (
                f"👤 <b>SHAXSIY KABINET</b>\n"
                f"{'=' * 30}\n\n"
                f"📝 <b>Ism:</b> {user[1]}\n"
                f"🎂 <b>Yosh:</b> {user[2]}\n"
                f"👔 <b>Rol:</b> {user[3]}\n"
                f"📞 <b>Telefon:</b> {user[4]}\n"
                f"📅 <b>Ro'yxatdan o'tgan:</b> {user[5][:10] if user[5] else 'Noma\'lum'}\n\n"
                f"📊 <b>STATISTIKA:</b>\n"
                f"• Jami murojaatlar: {len(await get_user_reports(message.from_user.id))}\n"
                f"• Yangi: {sum(1 for r in await get_user_reports(message.from_user.id) if r[11] == 'new')}\n"
                f"• Hal qilingan: {sum(1 for r in await get_user_reports(message.from_user.id) if r[11] == 'resolved')}\n"
                f"{'=' * 30}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Profilni tahrirlash", callback_data="edit_profile")],
                [InlineKeyboardButton(text="📋 Murojaatlarim", callback_data="my_reports")],
                [InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="main_menu")]
            ])
            await message.answer(profile_text, parse_mode='HTML', reply_markup=kb)
        else:
            await message.answer("❌ Xatolik!")
    else:
        await state.update_data(age=age)
        await state.set_state(UserStates.waiting_role)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👨‍💼 Xodim", callback_data="role_Xodim"),
                InlineKeyboardButton(text="🧍 Mijoz", callback_data="role_Mijoz")
            ],
            [InlineKeyboardButton(text="👤 Boshqa", callback_data="role_Boshqa")]
        ])

        await message.answer(
            "👔 <b>Siz kim sifatida murojaat qilmoqchisiz?</b>\n\n"
            "• <b>Xodim</b> - tashkilot xodimi\n"
            "• <b>Mijoz</b> - xizmat oluvchi\n"
            "• <b>Boshqa</b> - boshqa shaxs",
            parse_mode='HTML',
            reply_markup=kb
        )

@dp.callback_query(F.data.startswith("role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    role = callback.data.split("_")[1]
    await state.update_data(role=role)
    await state.set_state(UserStates.waiting_phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni ulashish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer(
        "📞 <b>Telefon raqamingizni yuboring:</b>\n\n"
        "Telefon raqamingizni ulashing yoki qo'lda kiriting.\n"
        "<i>Masalan: +998901234567</i>",
        parse_mode='HTML',
        reply_markup=kb
    )

@dp.message(UserStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()
        if len(phone) < 9:
            await message.answer("❌ Telefon raqam noto'g'ri. Qaytadan kiriting:")
            return

    data = await state.get_data()

    if 'editing' in data and data['editing'] == 'phone':
        success = await update_user(message.from_user.id, phone=phone)
        if success:
            await message.answer("✅ Telefon muvaffaqiyatli o'zgartirildi!")
            await state.clear()
            user = await get_user(message.from_user.id)
            profile_text = (
                f"👤 <b>SHAXSIY KABINET</b>\n"
                f"{'=' * 30}\n\n"
                f"📝 <b>Ism:</b> {user[1]}\n"
                f"🎂 <b>Yosh:</b> {user[2]}\n"
                f"👔 <b>Rol:</b> {user[3]}\n"
                f"📞 <b>Telefon:</b> {user[4]}\n"
                f"📅 <b>Ro'yxatdan o'tgan:</b> {user[5][:10] if user[5] else 'Noma\'lum'}\n\n"
                f"📊 <b>STATISTIKA:</b>\n"
                f"• Jami murojaatlar: {len(await get_user_reports(message.from_user.id))}\n"
                f"• Yangi: {sum(1 for r in await get_user_reports(message.from_user.id) if r[11] == 'new')}\n"
                f"• Hal qilingan: {sum(1 for r in await get_user_reports(message.from_user.id) if r[11] == 'resolved')}\n"
                f"{'=' * 30}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Profilni tahrirlash", callback_data="edit_profile")],
                [InlineKeyboardButton(text="📋 Murojaatlarim", callback_data="my_reports")],
                [InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="main_menu")]
            ])
            await message.answer(profile_text, parse_mode='HTML', reply_markup=kb)
        else:
            await message.answer("❌ Xatolik!")
    else:
        # Original registration code
        success = await add_user(
            message.from_user.id,
            data.get('fullname'),
            data.get('age'),
            data.get('role'),
            phone
        )
        if success:
            await state.clear()

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📩 Yangi murojaat", callback_data="new_report")],
                [InlineKeyboardButton(text="📋 Murojaatlarim", callback_data="my_reports")],
                [InlineKeyboardButton(text="👤 Profil", callback_data="profile")]
            ])

            await message.answer(
                "✅ <b>Ro'yxatdan o'tish muvaffaqiyatli!</b>\n\n"
                "Endi siz murojaat yuborishingiz mumkin.",
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()
            )
            await message.answer(
                f"🖐 <b>Assalomu alaykum, {data.get('fullname')}!</b>\n\n"
                f"👔 <b>Rol:</b> {data.get('role')}\n"
                f"📞 <b>Telefon:</b> {phone}\n\n"
                "Quyidagi bo'limlardan birini tanlang:",
                parse_mode='HTML',
                reply_markup=kb
            )
        else:
            await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring!")

# ==================== YANGI MUROJAAT ====================
@dp.callback_query(F.data == "new_report")
async def new_report(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Avval ro'yxatdan o'ting!")
        return

    await state.update_data(
        user_id=callback.from_user.id,
        fullname=user[1],
        age=user[2],
        role=user[3],
        phone=user[4]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Anonim murojaat", callback_data="anon_yes")],
        [InlineKeyboardButton(text="👁 Ochiq murojaat", callback_data="anon_no")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])

    await callback.message.edit_text(
        "🔐 <b>Murojaat turini tanlang:</b>\n\n"
        "🔒 <b>Anonim</b> - Shaxsiyatni ma'lum qilmaslik\n"
        "👁 <b>Ochiq</b> - Ochiq murojaat yo'llash",
        parse_mode='HTML',
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("anon_"))
async def process_anonymous(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    anonymous = callback.data == "anon_yes"
    await state.update_data(anonymous=anonymous)
    await state.set_state(UserStates.waiting_message)

    await callback.message.edit_text(
        "📝 <b>Murojaat matnini yozing:</b>\n\n"
        "Korrupsion holat bo'yicha batafsil ma'lumot bering:\n\n"
        "• Qayerda sodir bo'lgan?\n"
        "• Qachon sodir bo'lgan?\n"
        "• Kim ishtirok etgan?\n"
        "• Qanday voqea bo'lgan?\n\n"
        "⚠️ Iloji boricha aniq va batafsil yozing!",
        parse_mode='HTML'
    )

@dp.message(UserStates.waiting_message)
async def process_message(message: Message, state: FSMContext):
    msg_text = message.text.strip()

    if len(msg_text) < 10:
        await message.answer("❌ Matn juda qisqa. Kamida 10 ta belgi kiriting:")
        return

    await state.update_data(message=msg_text)
    await state.set_state(UserStates.waiting_file)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Dalil yuklash", callback_data="upload_file")],
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="skip_file")]
    ])

    await message.answer(
        "📎 <b>Dalil yuklash:</b>\n\n"
        "Agar sizda dalil bo'lsa (rasm, video, hujjat), yuboring.",
        parse_mode='HTML',
        reply_markup=kb
    )

@dp.callback_query(F.data == "upload_file")
async def upload_file_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "📎 <b>Faylni yuboring:</b>\n\n"
        "Rasm, video yoki hujjat yuboring.",
        parse_mode='HTML'
    )

@dp.callback_query(F.data == "skip_file")
async def skip_file(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(file_path=None, file_type=None)
    await confirm_and_send(callback.message, state)

@dp.message(UserStates.waiting_file, F.photo | F.document | F.video)
async def process_file_upload(message: Message, state: FSMContext):
    file_path, file_type = await save_file_from_message(message)

    if file_path:
        await state.update_data(file_path=file_path, file_type=file_type)
        await confirm_and_send(message, state)
    else:
        await message.answer("❌ Faylni yuklashda xatolik! Qaytadan urinib ko'ring.")

async def confirm_and_send(message: Message, state: FSMContext):
    data = await state.get_data()

    fullname = "Anonim" if data.get('anonymous') else data.get('fullname')

    confirm_text = (
        "✅ <b>Tasdiqlash</b>\n\n"
        f"👤 <b>Ism:</b> {fullname}\n"
        f"👔 <b>Rol:</b> {data.get('role')}\n"
        f"🔐 <b>Tur:</b> {'🔒 Anonim' if data.get('anonymous') else '👁 Ochiq'}\n\n"
        f"📝 <b>Murojaat:</b>\n{data.get('message')}\n\n"
        f"📎 <b>Dalil:</b> {'✅ Yuklangan' if data.get('file_path') else '❌ Yuq'}\n\n"
        "Murojaatni yuboraymi?"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="confirm_send")],
        [InlineKeyboardButton(text="✏️ Matnni o'zgartirish", callback_data="edit_message")],
        [InlineKeyboardButton(text="📎 Faylni o'zgartirish", callback_data="edit_file")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])

    await message.answer(confirm_text, parse_mode='HTML', reply_markup=kb)

@dp.callback_query(F.data == "edit_message")
async def edit_message(callback: CallbackQuery, state: FSMContext):
    """Murojaat matnini qayta yozish"""
    await callback.answer()
    await state.set_state(UserStates.waiting_message)

    await callback.message.edit_text(
        "📝 <b>Murojaat matnini qayta yozing:</b>\n\n"
        "Korrupsiya holati haqida batafsil ma'lumot bering:",
        parse_mode='HTML'
    )

@dp.callback_query(F.data == "edit_file")
async def edit_file(callback: CallbackQuery, state: FSMContext):
    """Murojaat faylini qayta yuklash"""
    await callback.answer()
    await state.set_state(UserStates.waiting_file)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Dalil yuklash", callback_data="upload_file")],
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="skip_file")]
    ])

    await callback.message.edit_text(
        "📎 <b>Yangi dalil yuklash:</b>\n\n"
        "Agar sizda dalil bo'lsa (rasm, video, hujjat), yuboring.",
        parse_mode='HTML',
        reply_markup=kb
    )

@dp.callback_query(F.data == "confirm_send")
async def confirm_send(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    try:
        report_id = await save_report(data)

        if report_id:
            await send_to_admin(report_id)

            # Yangi tugmalar bilan xabar
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📩 Yana murojaat yuborish", callback_data="new_report")],
                [InlineKeyboardButton(text="📋 Murojaatlarimni ko'rish", callback_data="my_reports")],
                [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")]
            ])

            await callback.message.edit_text(
                f"✅ <b>MUROJAAT YUBORILDI!</b>\n\n"
                f"📋 Murojaat raqami: <code>#{report_id}</code>\n\n"
                f"Sizning murojaatingiz adminga yuborildi.\n"
                f"Tez orada javob olasiz!\n\n"
                f"Yana murojaat yuborishingiz mumkin.",
                parse_mode='HTML',
                reply_markup=kb
            )
        else:
            await callback.message.answer("❌ Murojaat yuborishda xatolik!")

        await state.clear()

    except Exception as e:
        logger.error(f"❌ Murojaat yuborishda xatolik: {e}")
        await callback.message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring!")

# ==================== PROFIL VA MUROJAATLAR ====================
@dp.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    await callback.answer()

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Profil topilmadi! Avval ro'yxatdan o'ting.")
        return

    reports = await get_user_reports(callback.from_user.id)
    total_reports = len(reports)
    new_reports = sum(1 for r in reports if r[11] == 'new')
    resolved_reports = sum(1 for r in reports if r[11] == 'resolved')

    profile_text = (
        f"👤 <b>SHAXSIY KABINET</b>\n"
        f"{'=' * 30}\n\n"
        f"📝 <b>Ism:</b> {user[1]}\n"
        f"🎂 <b>Yosh:</b> {user[2]}\n"
        f"👔 <b>Rol:</b> {user[3]}\n"
        f"📞 <b>Telefon:</b> {user[4]}\n"
        f"📅 <b>Ro'yxatdan o'tgan:</b> {user[5][:10] if user[5] else 'Noma\'lum'}\n\n"
        f"📊 <b>STATISTIKA:</b>\n"
        f"• Jami murojaatlar: {total_reports}\n"
        f"• Yangi: {new_reports}\n"
        f"• Hal qilingan: {resolved_reports}\n"
        f"{'=' * 30}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Profilni tahrirlash", callback_data="edit_profile")],
        [InlineKeyboardButton(text="📋 Murojaatlarim", callback_data="my_reports")],
        [InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="main_menu")]
    ])

    await callback.message.edit_text(profile_text, parse_mode='HTML', reply_markup=kb)

@dp.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery):
    await callback.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Ismni o'zgartirish", callback_data="edit_name")],
        [InlineKeyboardButton(text="🎂 Yoshni o'zgartirish", callback_data="edit_age")],
        [InlineKeyboardButton(text="👔 Rolni o'zgartirish", callback_data="edit_role")],
        [InlineKeyboardButton(text="📞 Telefonni o'zgartirish", callback_data="edit_phone")],
        [InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="main_menu")]
    ])

    await callback.message.edit_text(
        "✏️ <b>PROFILNI TAHRIRLASH</b>\n\n"
        "Nimani o'zgartirmoqchisiz?",
        parse_mode='HTML',
        reply_markup=kb
    )

@dp.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(editing='name')
    await state.set_state(UserStates.waiting_fullname)
    await callback.message.answer("👤 Yangi ismingizni kiriting:")

@dp.callback_query(F.data == "edit_age")
async def edit_age(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(editing='age')
    await state.set_state(UserStates.waiting_age)
    await callback.message.answer("🎂 Yangi yoshingizni kiriting:")

@dp.callback_query(F.data == "edit_role")
async def edit_role(callback: CallbackQuery):
    await callback.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨‍💼 Xodim", callback_data="role_Xodim_edit"),
            InlineKeyboardButton(text="🧍 Mijoz", callback_data="role_Mijoz_edit")
        ],
        [InlineKeyboardButton(text="👤 Boshqa", callback_data="role_Boshqa_edit")]
    ])

    await callback.message.edit_text("👔 Yangi rolingizni tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("role_") & F.data.endswith("_edit"))
async def update_role(callback: CallbackQuery):
    await callback.answer()
    role = callback.data.split("_")[1]

    success = await update_user(callback.from_user.id, role=role)
    if success:
        await callback.message.answer("✅ Rol muvaffaqiyatli o'zgartirildi!")
        await show_profile(callback)
    else:
        await callback.message.answer("❌ Xatolik yuz berdi!")

@dp.callback_query(F.data == "edit_phone")
async def edit_phone(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(editing='phone')
    await state.set_state(UserStates.waiting_phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer("📞 Yangi telefon raqamingizni kiriting:", reply_markup=kb)

@dp.callback_query(F.data == "my_reports")
async def my_reports(callback: CallbackQuery):
    await callback.answer()

    reports = await get_user_reports(callback.from_user.id)

    if not reports:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📩 Yangi murojaat", callback_data="new_report")],
            [InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="main_menu")]
        ])
        await callback.message.edit_text(
            "📋 <b>MUROJAATLARINGIZ</b>\n\n"
            "Sizda hali murojaatlar yo'q.\n\n"
            "Yangi murojaat yuborish uchun tugmani bosing.",
            parse_mode='HTML',
            reply_markup=kb
        )
        return

    text = "📋 <b>SIZNING MUROJAATLARINGIZ</b>\n" + "=" * 30 + "\n\n"
    kb = []

    for report in reports[:10]:
        rid, status, date = report[0], report[11], report[10]
        status_emoji = {"new": "🆕", "processing": "⏳", "resolved": "✅"}.get(status, "❓")

        text += f"{status_emoji} #{rid} - {date[:16]}\n"
        kb.append([InlineKeyboardButton(
            text=f"{status_emoji} #{rid} - {date[:10]}",
            callback_data=f"view_report_{rid}"
        )])

    kb.append([InlineKeyboardButton(text="📩 Yangi murojaat", callback_data="new_report")])
    kb.append([InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="main_menu")])

    await callback.message.edit_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@dp.callback_query(F.data.startswith("view_report_"))
async def view_report(callback: CallbackQuery):
    await callback.answer()

    report_id = int(callback.data.split("_")[2])
    report = await get_report(report_id)

    if not report:
        await callback.answer("❌ Murojaat topilmadi!", show_alert=True)
        return

    rid, user_id, fullname, age, role, phone, anonymous, message, file_path, file_type, date, status, admin_reply = report

    status_text = {"new": "🆕 Yangi", "processing": "⏳ Ko'rib chiqilmoqda", "resolved": "✅ Hal qilingan"}.get(status, "❓")

    report_text = (
        f"📋 <b>MUROJAAT #{rid}</b>\n"
        f"{'=' * 30}\n\n"
        f"📅 <b>Sana:</b> {date}\n"
        f"📊 <b>Status:</b> {status_text}\n"
        f"🔐 <b>Tur:</b> {'🔒 Anonim' if anonymous else '👁 Ochiq'}\n\n"
        f"📝 <b>Murojaat matni:</b>\n{message}\n\n"
        f"📎 <b>Dalil:</b> {"✅ Mavjud' if file_path else '❌ Yo`q"}\n"
    )

    if admin_reply:
        report_text += f"\n💬 <b>Admin javobi:</b>\n{admin_reply}\n"

    report_text += f"{'=' * 30}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="my_reports")]
    ])

    await callback.message.edit_text(report_text, parse_mode='HTML', reply_markup=kb)

# ==================== ADMIN PANEL ====================
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("❌ Siz admin emassiz!")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Barcha murojaatlar", callback_data="admin_all"),
            InlineKeyboardButton(text="🆕 Yangilar", callback_data="admin_new")
        ],
        [
            InlineKeyboardButton(text="⏳ Jarayonda", callback_data="admin_processing"),
            InlineKeyboardButton(text="✅ Hal qilingan", callback_data="admin_resolved")
        ],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📥 Excel yuklash", callback_data="admin_export")],
    ])

    await callback.message.edit_text(
        "🎛 <b>ADMIN PANEL</b>\n\n"
        "Bo'limni tanlang:",
        parse_mode='HTML',
        reply_markup=kb
    )

@dp.callback_query(F.data == "admin_export")
async def admin_export(callback: CallbackQuery):
    await callback.answer("Excel fayl tayyorlanmoqda...")

    reports = await get_full_reports()
    if not reports:
        await callback.message.answer("❌ Murojaatlar yo'q!")
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    headers = ['ID', 'User ID', 'Fullname', 'Age', 'Role', 'Phone', 'Anonymous', 'Message', 'File Path', 'File Type', 'Created At', 'Status', 'Admin Reply']
    ws.append(headers)

    for report in reports:
        ws.append(list(report))

    file_name = f"reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    file_path = os.path.join(UPLOADS_DIR, file_name)
    wb.save(file_path)

    try:
        await bot.send_document(callback.from_user.id, FSInputFile(file_path), caption="📥 Barcha murojaatlar Excel formatida")
        os.remove(file_path)
    except Exception as e:
        logger.error(f"❌ Excel yuborishda xatolik: {e}")
        await callback.message.answer("❌ Excel faylni yuborishda xatolik!")
        if os.path.exists(file_path):
            os.remove(file_path)

@dp.callback_query(F.data.in_({"admin_all", "admin_new", "admin_processing", "admin_resolved", "admin_stats", "admin_export"}))
async def admin_reports_list(callback: CallbackQuery):
    await callback.answer()

    action = callback.data.split("_")[1]

    if action == "stats":
        await show_admin_stats(callback)
        return

    if action == "export":
        await admin_export(callback)
        return

    status_map = {"new": "new", "processing": "processing", "resolved": "resolved", "all": None}
    status = status_map.get(action)

    reports = await get_all_reports(status=status, limit=50)

    if not reports:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_panel")]
        ])
        await callback.message.edit_text("📋 Murojaatlar yo'q.", reply_markup=kb)
        return

    title_map = {
        "all": "BARCHA MUROJAATLAR",
        "new": "YANGI MUROJAATLAR",
        "processing": "JARAYONDAGI MUROJAATLAR",
        "resolved": "HAL QILINGAN MUROJAATLAR"
    }

    text = f"📋 <b>{title_map[action]}</b>\n" + "=" * 30 + "\n\n"
    kb = []

    for report in reports[:20]:
        rid, date, status, fullname = report
        status_emoji = {"new": "🆕", "processing": "⏳", "resolved": "✅"}.get(status, "❓")

        text += f"{status_emoji} #{rid} - {fullname} - {date[:16]}\n"
        kb.append([InlineKeyboardButton(
            text=f"{status_emoji} #{rid} - {fullname[:15]}",
            callback_data=f"admin_view_{rid}"
        )])

    kb.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"admin_{action}")])
    kb.append([InlineKeyboardButton(text="◶ Admin Panel", callback_data="admin_panel")])

    await callback.message.edit_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

async def show_admin_stats(callback: CallbackQuery):
    stats = await get_stats()

    stats_text = (
        f"📊 <b>STATISTIKA</b>\n"
        f"{'=' * 30}\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {stats.get('total_users', 0)}\n"
        f"📋 <b>Jami murojaatlar:</b> {stats.get('total_reports', 0)}\n\n"
        f"📈 <b>STATUS BO'YICHA:</b>\n"
        f"• 🆕 Yangi: {stats.get('new_reports', 0)}\n"
        f"• ⏳ Ko'rilmoqda: {stats.get('processing_reports', 0)}\n"
        f"• ✅ Hal qilingan: {stats.get('resolved_reports', 0)}\n"
        f"• 🔒 Anonim: {stats.get('anonymous_reports', 0)}\n"
        f"{'=' * 30}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◶ Admin Panel", callback_data="admin_panel")]
    ])

    await callback.message.edit_text(stats_text, parse_mode='HTML', reply_markup=kb)

@dp.callback_query(F.data.startswith("admin_view_"))
async def admin_view_report(callback: CallbackQuery):
    await callback.answer()

    report_id = int(callback.data.split("_")[2])
    report = await get_report(report_id)

    if not report:
        await callback.answer("❌ Murojaat topilmadi!", show_alert=True)
        return

    rid, user_id, fullname, age, role, phone, anonymous, message, file_path, file_type, date, status, admin_reply = report

    status_text = {"new": "🆕 Yangi", "processing": "⏳ Ko'rib chiqilmoqda", "resolved": "✅ Hal qilingan"}.get(status, "❓")

    report_text = (
        f"📋 <b>MUROJAAT #{rid}</b>\n"
        f"{'=' * 30}\n\n"
        f"📅 <b>Sana:</b> {date}\n"
        f"📊 <b>Status:</b> {status_text}\n"
        f"🔐 <b>Tur:</b> {'🔒 Anonim' if anonymous else '👁 Ochiq'}\n\n"
        f"📝 <b>Murojaat matni:</b>\n{message}\n\n"
        f"📎 <b>Dalil:</b> {"✅ Mavjud' if file_path else '❌ Yo`q"}\n"
    )

    if admin_reply:
        report_text += f"\n💬 <b>Admin javobi:</b>\n{admin_reply}\n"

    report_text += f"{'=' * 30}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_all")]
    ])

    await callback.message.edit_text(report_text, parse_mode='HTML', reply_markup=kb)

@dp.callback_query(F.data.startswith("status_"))
async def change_status(callback: CallbackQuery):
    parts = callback.data.split("_")
    new_status = parts[1]
    report_id = int(parts[2])

    success = await update_report_status(report_id, new_status)

    if success:
        status_names = {"processing": "⏳ Ko'rib chiqilmoqda", "resolved": "✅ Hal qilingan"}
        await callback.answer(f"✅ Status: {status_names[new_status]}", show_alert=True)

        # Foydalanuvchiga xabar yuborish
        report = await get_report(report_id)
        if report:
            try:
                await bot.send_message(
                    report[1],
                    f"📊 <b>Murojaat #{report_id} statusi o'zgartirildi!</b>\n\n"
                    f"Yangi status: {status_names[new_status]}",
                    parse_mode='HTML'
                )
            except:
                pass

        await admin_view_report(callback)
    else:
        await callback.answer("❌ Xatolik!", show_alert=True)

@dp.callback_query(F.data.startswith("view_file_"))
async def view_file_admin(callback: CallbackQuery):
    await callback.answer()

    report_id = int(callback.data.split("_")[2])
    report = await get_report(report_id)

    if not report or not report[8]:
        await callback.answer("❌ Fayl topilmadi!", show_alert=True)
        return

    file_path = report[8]
    file_type = report[9]

    if not os.path.exists(file_path):
        await callback.answer("❌ Fayl o'chirilgan!", show_alert=True)
        return

    try:
        file = FSInputFile(file_path)
        caption = f"📎 Murojaat #{report_id} dalili"

        if file_type == "photo":
            await callback.message.answer_photo(photo=file, caption=caption)
        elif file_type == "video":
            await callback.message.answer_video(video=file, caption=caption)
        elif file_type == "document":
            await callback.message.answer_document(document=file, caption=caption)

        await callback.answer("✅ Fayl yuborildi")
    except Exception as e:
        logger.error(f"❌ Fayl yuborishda xatolik: {e}")
        await callback.answer("❌ Xatolik!", show_alert=True)

@dp.callback_query(F.data.startswith("reply_"))
async def reply_to_user(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    report_id = int(callback.data.split("_")[1])
    report = await get_report(report_id)

    if not report:
        await callback.answer("❌ Murojaat topilmadi!", show_alert=True)
        return

    await state.update_data(reply_report_id=report_id, reply_user_id=report[1])
    await state.set_state(AdminStates.waiting_response)

    await callback.message.answer(
        f"💬 <b>Murojaat #{report_id} uchun javob yozing:</b>\n\n"
        f"Javobingizni yuboring:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor qilish ❌", callback_data="cancel_reply")]
        ])
    )

@dp.callback_query(F.data == "cancel_reply")
async def cancel_reply(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Bekor qilindi")
    await state.clear()
    await callback.message.edit_text("❌ Javob yuborish bekor qilindi.")

@dp.message(AdminStates.waiting_response)
async def process_admin_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    report_id = data['reply_report_id']
    user_id = data['reply_user_id']

    try:
        # Javobni saqlash
        success = await add_admin_reply(report_id, message.text)

        if success:
            # Foydalanuvchiga yuborish
            await bot.send_message(
                user_id,
                f"💬 <b>#{report_id} raqamli murojaatingizga javob:</b>\n\n"
                f"{message.text}\n\n"
                f"{'=' * 30}\n"
                f"<i>Antikorrupsiya bo'limi</i>",
                parse_mode='HTML'
            )

            await message.answer(
                f"✅ <b>Javob yuborildi!</b>\n\n"
                f"Murojaat: #{report_id}\n"
                f"Foydalanuvchi: {user_id}",
                parse_mode='HTML'
            )
        else:
            await message.answer("❌ Javob saqlashda xatolik!")

        await state.clear()

    except Exception as e:
        logger.error(f"❌ Javob yuborishda xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi!")

@dp.callback_query(F.data.startswith("delete_confirm_"))
async def delete_report_handler(callback: CallbackQuery):
    await callback.answer()

    report_id = int(callback.data.split("_")[2])

    try:
        success = await delete_report(report_id)
        if success:
            await callback.message.edit_text(
                f"✅ Murojaat #{report_id} o'chirildi!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◶ Admin Panel", callback_data="admin_panel")]
                ])
            )
        else:
            await callback.answer("❌ O'chirishda xatolik!", show_alert=True)
    except Exception as e:
        logger.error(f"❌ O'chirishda xatolik: {e}")
        await callback.answer("❌ Xatolik!", show_alert=True)

# ==================== UMUMIY HANDLERS ====================
@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Bekor qilindi")
    await state.clear()
    user = await get_user(callback.from_user.id)
    if user:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📩 Yangi murojaat", callback_data="new_report")],
            [InlineKeyboardButton(text="📋 Murojaatlarim", callback_data="my_reports")],
            [InlineKeyboardButton(text="👤 Profil", callback_data="profile")]
        ])
        await callback.message.edit_text(
            f"🖐 <b>Assalomu alaykum, {user[1]}!</b>\n\n"
            f"👔 <b>Rol:</b> {user[3]}\n"
            f"📞 <b>Telefon:</b> {user[4]}\n\n"
            "Quyidagi bo'limlardan birini tanlang:",
            parse_mode='HTML',
            reply_markup=kb
        )
    else:
        await start_handler(callback.message, state)

@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    user = await get_user(callback.from_user.id)
    if user:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📩 Yangi murojaat", callback_data="new_report")],
            [InlineKeyboardButton(text="📋 Murojaatlarim", callback_data="my_reports")],
            [InlineKeyboardButton(text="👤 Profil", callback_data="profile")]
        ])
        await callback.message.edit_text(
            f"🖐 <b>Assalomu alaykum, {user[1]}!</b>\n\n"
            f"👔 <b>Rol:</b> {user[3]}\n"
            f"📞 <b>Telefon:</b> {user[4]}\n\n"
            "Quyidagi bo'limlardan birini tanlang:",
            parse_mode='HTML',
            reply_markup=kb
        )
    else:
        await start_handler(callback.message, state)

@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = (
        "ℹ️ <b>YORDAM</b>\n"
        f"{'=' * 30}\n\n"
        "<b>Botdan foydalanish:</b>\n\n"
        "1️⃣ /start - Boshlash\n"
        "2️⃣ Ro'yxatdan o'tish\n"
        "3️⃣ Murojaat yuborish\n"
        "4️⃣ Javob olish\n\n"
        "<b>Xususiyatlar:</b>\n"
        "• Anonim murojaatlar\n"
        "• Dalil yuklash\n"
        "• Status kuzatish\n"
        "• Shaxsiy kabinet\n\n"
        "📞 Yordam: @admin"
    )

    await message.answer(help_text, parse_mode='HTML')

# ==================== MAIN ====================
async def on_startup():
    await init_db()
    logger.info("✅ Bot ishga tushdi!")

    try:
        await bot.send_message(
            ADMIN_ID,
            f"🤖 <b>BOT ISHGA TUSHDI!</b>\n\n"
            f"⏰ Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode='HTML'
        )
    except:
        logger.warning("❌ Adminga xabar yuborib bo'lmadi")

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("❌ Bot to'xtatildi (Ctrl+C)")