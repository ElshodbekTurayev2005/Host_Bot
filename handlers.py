from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from config import bot, ADMIN_ID
from utils import save_file_from_message, send_to_admin, show_confirm
from database import save_report, get_reports, get_report_by_id, delete_report

router = Router()

class UserStates(StatesGroup):
    waiting_fullname = State()
    waiting_lastname = State()
    waiting_age = State()
    waiting_phone = State()
    waiting_role = State()
    waiting_anonymous = State()
    waiting_message = State()
    waiting_file = State()
    waiting_confirm = State()

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await show_admin_panel(message)
        return

    await state.update_data(user_id=message.from_user.id)
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "Bu bot orqali korrupsion holatlar haqida Antikorrupsiya bo‘limiga murojaat yuborishingiz mumkin.\n"
        "Iltimos, quyidagi bosqichlarni to‘ldiring 👇"
    )
    await state.set_state(UserStates.waiting_fullname)
    await message.answer("Ismingizni kiriting:")

@router.message(UserStates.waiting_fullname)
async def process_fullname(message: Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    await state.set_state(UserStates.waiting_lastname)
    await message.answer("Familiyangizni kiriting:")

@router.message(UserStates.waiting_lastname)
async def process_lastname(message: Message, state: FSMContext):
    data = await state.get_data()
    fullname = f"{data['fullname']} {message.text}"
    await state.update_data(fullname=fullname)
    await state.set_state(UserStates.waiting_age)
    await message.answer("Yoshingizni kiriting:")

@router.message(UserStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, raqam kiriting.")
        return
    await state.update_data(age=int(message.text))
    await state.set_state(UserStates.waiting_phone)
    await message.answer("Telefon raqamingizni kiriting (+998 formatda):")

@router.message(UserStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧑‍⚕️ Xodimman", callback_data="role_employee")],
        [InlineKeyboardButton(text="👤 Mijozman", callback_data="role_client")]
    ])
    await state.set_state(UserStates.waiting_role)
    await message.answer("Siz kim sifatida murojaat qilmoqchisiz?", reply_markup=kb)

@router.callback_query(F.data.startswith("role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    role = "Xodim" if callback.data == "role_employee" else "Mijoz"
    await state.update_data(role=role)
    await callback.answer()
    await callback.message.answer(f"Siz {role} sifatida murojaat qilmoqdasiz.")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Anonim", callback_data="anon_true")],
        [InlineKeyboardButton(text="👁 Ochiq", callback_data="anon_false")]
    ])
    await callback.message.answer("Murojaatingizni qanday yubormoqchisiz?", reply_markup=kb)

@router.callback_query(F.data.startswith("anon_"))
async def process_anonymous(callback: CallbackQuery, state: FSMContext):
    anonymous = callback.data == "anon_true"
    await state.update_data(anonymous=anonymous)
    await callback.answer()
    anon_text = "Anonim ravishda" if anonymous else "Ochiq ism bilan"
    await callback.message.answer(f"{anon_text} murojaat yubormoqdasiz.")
    await state.set_state(UserStates.waiting_message)
    await callback.message.answer("Iltimos, murojaat matnini yozing:")

@router.message(UserStates.waiting_message)
async def process_message(message: Message, state: FSMContext):
    await state.update_data(message=message.text)
    await state.set_state(UserStates.waiting_file)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Fayl yubormayman", callback_data="no_file")]
    ])
    await message.answer(
        "Endi dalil sifatida fayl yuborishingiz mumkin (ixtiyoriy):\n"
        "📷 Rasm | 🎥 Video | 📄 Fayl | 🎙 Ovozli xabar",
        reply_markup=kb
    )

@router.message(UserStates.waiting_file)
async def process_file(message: Message, state: FSMContext):
    file_path = await save_file_from_message(message)  # Ensure only message is passed
    await state.update_data(file_path=file_path)
    await show_confirm(message, state)

@router.callback_query(F.data == "no_file")
async def skip_file(callback: CallbackQuery, state: FSMContext):
    await state.update_data(file_path=None)
    await show_confirm(callback.message, state)
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_"))
async def confirm_report(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    if callback.data == "confirm_yes":
        try:
            report_id = await save_report(data)
            await send_to_admin(report_id)
            await callback.message.answer("📩 Rahmat! Murojaatingiz qabul qilindi.")
        except Exception as e:
            await callback.message.answer(f"❌ Xatolik yuz berdi: {e}")
        await state.clear()
    else:
        await callback.message.answer("Murojaat bekor qilindi. /start buyrug‘ini bosib qayta urinib ko‘ring.")
        await state.clear()

async def show_admin_panel(message: Message):
    try:
        reports = await get_reports()
        if not reports:
            await message.answer("Hozircha murojaatlar yo'q.")
            return

        text = "📋 So'nggi murojaatlar:\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for report in reports:
            rid, date = report
            text += f"#{rid} - {date}\n"
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"#{rid}", callback_data=f"admin_view_{rid}")])

        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh")])
        await message.answer(text, reply_markup=keyboard, parse_mode='Markdown')
    except Exception as e:
        await message.answer("Ma'lumotlarni yuklashda xatolik yuz berdi.")

@router.callback_query(lambda c: c.data.startswith("admin_view_"))
async def admin_view_report(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo'q!")
        return

    report_id = int(callback.data.split("_")[2])
    try:
        row = await get_report_by_id(report_id)
        if row:
            fullname, age, phone, role, anonymous, message, file_path, created_at = row[1:]
            text = (
                f"📄 Murojaat #{report_id}\n\n"
                f"Ism: {fullname}\n"
                f"Yosh: {age}\n"
                f"Telefon: {phone}\n"
                f"Rol: {role}\n"
                f"Anonim: {'Ha' if anonymous else 'Yo\'q'}\n"
                f"Sana: {created_at}\n\n"
                f"Matn:\n{message}"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
                [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin_delete_{report_id}")],
                [InlineKeyboardButton(text="📥 Yuklab olish", callback_data=f"admin_download_{report_id}") if file_path else InlineKeyboardButton(text="Dalil yo'q", callback_data="none")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
            await callback.answer()
    except Exception as e:
        await callback.answer("Ma'lumot yuklanmadi.")

@router.callback_query(lambda c: c.data.startswith("admin_delete_"))
async def admin_delete_report(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    report_id = int(callback.data.split("_")[2])
    try:
        await delete_report(report_id)
        await callback.message.answer(f"#{report_id} murojaati o'chirildi.")
        await show_admin_panel(callback.message)
        await callback.answer()
    except Exception as e:
        await callback.answer("O'chirishda xatolik yuz berdi.")

@router.callback_query(lambda c: c.data in ["admin_back", "admin_refresh"])
async def admin_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    try:
        await show_admin_panel(callback.message)
        await callback.answer()
    except Exception as e:
        await callback.answer("Ma'lumot yuklanmadi.")

@router.callback_query(lambda c: c.data.startswith("admin_download_"))
async def admin_download(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    report_id = int(callback.data.split("_")[2])
    try:
        row = await get_report_by_id(report_id)
        file_path = row[7] if row else None
        if file_path:
            document = FSInputFile(file_path)
            await bot.send_document(callback.from_user.id, document)
            await callback.answer("Fayl yuborildi!")
        else:
            await callback.answer("Bu murojaatda fayl yo'q.")
    except Exception as e:
        await callback.answer(f"Faylni yuborishda xatolik: {str(e)}")