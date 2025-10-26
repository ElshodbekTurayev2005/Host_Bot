import os
import uuid
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramBadRequest
from states import UserStates
from config import bot, ADMIN_ID


# --- show_confirm funksiyasi ---
async def show_confirm(message: Message, state: FSMContext):
    """Foydalanuvchiga murojaatni tasdiqlash uchun xabar yuboradi."""
    data = await state.get_data()

    fullname_show = "Anonim" if data.get('anonymous', False) else data.get('fullname', 'Nomaʼlum')
    file_text = "mavjud" if data.get('file_path') else "mavjud emas"

    confirm_text = (
        "✅ <b>Murojaatingiz tayyor.</b>\n"
        "Quyidagi ma’lumotlar yuboriladi:\n\n"
        f"<b>Ism Familiya:</b> {fullname_show}\n"
        f"<b>Yosh:</b> {data.get('age', 'Nomaʼlum')}\n"
        f"<b>Telefon:</b> {data.get('phone', 'Nomaʼlum')}\n"
        f"<b>Kim:</b> {data.get('role', 'Nomaʼlum')}\n"
        f"<b>Murojaat matni:</b> {data.get('message', 'Nomaʼlum')}\n"
        f"<b>Dalillar:</b> {file_text}\n\n"
        "Tasdiqlaysizmi?"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Yo‘q, tahrirlash", callback_data="edit_report")]
    ])

    try:
        await message.answer(confirm_text, reply_markup=keyboard, parse_mode='HTML')
        await state.set_state(UserStates.waiting_confirm)
    except TelegramBadRequest as e:
        print(f"Xabar yuborishda xatolik: {e}")


# --- save_file funksiyasi ---
async def save_file(file_id: str, file_type: str) -> str:
    """Foydalanuvchi yuborgan faylni yuklab olish va saqlash."""
    try:
        file = await bot.get_file(file_id)
        unique_filename = f"{uuid.uuid4()}_{os.path.basename(file.file_path)}"
        save_dir = os.path.join("uploads", file_type)
        os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, unique_filename)
        await bot.download_file(file.file_path, save_path)
        return save_path
    except Exception as e:
        print(f"Faylni saqlashda xatolik: {e}")
        return ""


# --- send_to_admin funksiyasi ---
async def send_to_admin(report_id: int):
    """Admin uchun murojaat haqida xabar yuborish."""
    from database import get_report_by_id

    try:
        row = await get_report_by_id(report_id)
        if not row:
            print(f"Report topilmadi: {report_id}")
            return

        # --- Ma'lumotlar bazasidagi ustunlar tartibi ---
        id_, fullname, age, phone, role, anonymous, message_text, file_path, created_at = row[:9]

        text = (
            f"📩 <b>Yangi murojaat #{id_}</b>\n\n"
            f"👤 <b>Ism:</b> {fullname}\n"
            f"🎂 <b>Yosh:</b> {age}\n"
            f"📞 <b>Telefon:</b> {phone}\n"
            f"👔 <b>Kim:</b> {role}\n"
            f"🕵️ <b>Anonim:</b> {'Ha' if anonymous else 'Yo‘q'}\n"
            f"🕒 <b>Sana:</b> {created_at}\n\n"
            f"📝 <b>Matn:</b>\n{message_text}"
        )

        # --- Admin uchun xabar yuborish ---
        await bot.send_message(ADMIN_ID, text, parse_mode='HTML')

        # --- Fayl mavjud bo‘lsa, yuborish ---
        if file_path and os.path.exists(file_path) and os.path.isfile(file_path):
            await bot.send_document(ADMIN_ID, FSInputFile(file_path))

    except TelegramBadRequest as e:
        print(f"Admin xabarini yuborishda xatolik: {e}")
    except Exception as e:
        print(f"send_to_admin xatosi: {e}")


# --- save_file_from_message funksiyasi ---
async def save_file_from_message(message: Message) -> str:
    """Xabar ichidagi faylni saqlaydi (universal)."""
    file_path = None
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            file_path = await save_file(file_id, "photo")
        elif message.document:
            file_id = message.document.file_id
            file_path = await save_file(file_id, "document")
        elif message.video:
            file_id = message.video.file_id
            file_path = await save_file(file_id, "video")
        elif message.voice:
            file_id = message.voice.file_id
            file_path = await save_file(file_id, "voice")
        elif message.audio:
            file_id = message.audio.file_id
            file_path = await save_file(file_id, "audio")
    except Exception as e:
        print(f"Faylni qayta ishlashda xatolik: {e}")
    return file_path
