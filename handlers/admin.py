from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, update
from database.models import Settings
from database.db import get_session
from config import ADMIN_ID, FILE_PRICE


class AdminStates(StatesGroup):
    waiting_for_link = State()
    selecting_language = State()


router = Router()


@router.callback_query(F.data == "admin_settings")
async def admin_settings_handler(callback: CallbackQuery):
    """Admin asosiy menyusi"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Sizda bu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    text = (
        "⚙️ *Admin Sozlamalar*\n\n"
        "👇 Qaysi bo'limni o'zgartirmoqchisiz?"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Ommaviy Oferta", callback_data="admin_offer")],
        [InlineKeyboardButton(text="💰 Narx Sozlamalari", callback_data="admin_price")],
        [InlineKeyboardButton(text="⚙️ Boshqa Sozlamalar", callback_data="admin_other")],
    ])

    await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# --- OFERTA SOZLAMALARI ---
@router.callback_query(F.data == "admin_offer")
async def admin_offer_handler(callback: CallbackQuery):
    """Ommaviy oferta sozlamalari"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Sizda bu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    async for session in get_session():
        stmt = select(Settings).limit(1)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()

        if not settings:
            settings = Settings(uz_offer="", ru_offer="", en_offer="")
            session.add(settings)
            await session.commit()

    uz_offer = settings.uz_offer or "❌ Belgilanmagan"
    ru_offer = settings.ru_offer or "❌ Belgilanmagan"
    en_offer = settings.en_offer or "❌ Belgilanmagan"

    text = (
        "📜 *Ommaviy Oferta Linklari*\n\n"
        f"🇺🇿 O'zbek: {uz_offer}\n"
        f"🇷🇺 Русский: {ru_offer}\n"
        f"🇬🇧 English: {en_offer}\n\n"
        "👇 O'zgartirish uchun tilni tanlang:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek linkini o'zgartirish", callback_data="edit_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский linkini o'zgartirish", callback_data="edit_ru")],
        [InlineKeyboardButton(text="🇬🇧 English linkini o'zgartirish", callback_data="edit_en")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_settings")],
    ])

    await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# --- Til tanlash callback ---
@router.callback_query(F.data.startswith("edit_"))
async def edit_language_callback(callback: CallbackQuery, state: FSMContext):
    """Til tanlanganda state o'rnatadi"""
    lang_map = {
        "edit_uz": "uz",
        "edit_ru": "ru",
        "edit_en": "en"
    }
    lang = lang_map.get(callback.data)
    
    if not lang:
        return
    
    await state.set_state(AdminStates.waiting_for_link)
    await state.update_data(lang=lang)
    
    lang_name = {"uz": "O'zbek", "ru": "Русский", "en": "English"}.get(lang)
    await callback.message.answer(f"🔗 {lang_name} uchun yangi linkni yuboring:")
    await callback.answer()


# --- Link xabarini qabul qilish ---
@router.message(AdminStates.waiting_for_link)
async def receive_link(message: Message, state: FSMContext):
    """Link qabul qiladi va bazaga saqlaydi"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Sizda bu operatsiyaga huquqi yo'q.")
        return
    
    link = message.text.strip()
    
    # Link tekshiruvi
    if not link.startswith(("http://", "https://")):
        await message.answer("❌ Link http:// yoki https:// bilan boshlanishi kerak!")
        return
    
    data = await state.get_data()
    lang = data.get("lang")
    
    try:
        async for session in get_session():
            stmt = select(Settings).limit(1)
            result = await session.execute(stmt)
            settings = result.scalar_one_or_none()
            
            if not settings:
                settings = Settings(uz_offer="", ru_offer="", en_offer="")
                session.add(settings)
                await session.flush()
            
            if lang == "uz":
                settings.uz_offer = link
            elif lang == "ru":
                settings.ru_offer = link
            elif lang == "en":
                settings.en_offer = link
            
            await session.commit()
            
            # Yangilangan sozlamalarni o'qib olamiz
            result = await session.execute(stmt)
            updated_settings = result.scalar_one_or_none()
        
        lang_name = {"uz": "O'zbek", "ru": "Русский", "en": "English"}.get(lang)
        await message.answer(f"✅ {lang_name} oferta linki muvaffaqiyatli saqlandi!\n🔗 {link}")
        
        # Oferta menyusini qayta chiqaramiz
        await show_offer_menu(message, updated_settings)
    
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    
    finally:
        await state.clear()


async def show_offer_menu(message: Message, settings: Settings):
    """Oferta sozlamalar menyusini ko'rsatadi"""
    uz_offer = settings.uz_offer or "❌ Belgilanmagan"
    ru_offer = settings.ru_offer or "❌ Belgilanmagan"
    en_offer = settings.en_offer or "❌ Belgilanmagan"

    text = (
        "📜 *Ommaviy Oferta Linklari*\n\n"
        f"🇺🇿 O'zbek: {uz_offer}\n"
        f"🇷🇺 Русский: {ru_offer}\n"
        f"🇬🇧 English: {en_offer}\n\n"
        "👇 O'zgartirish uchun tilni tanlang:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek linkini o'zgartirish", callback_data="edit_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский linkini o'zgartirish", callback_data="edit_ru")],
        [InlineKeyboardButton(text="🇬🇧 English linkini o'zgartirish", callback_data="edit_en")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_settings")],
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


# --- NARX SOZLAMALARI ---
@router.callback_query(F.data == "admin_price")
async def admin_price_handler(callback: CallbackQuery):
    """Narx sozlamalari"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Sizda bu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    current_price = FILE_PRICE
    
    text = (
        "💰 *Narx Sozlamalari*\n\n"
        f"Hozirgi narx: {current_price} so'm\n\n"
        "👇 O'zgartirish uchun tugmani bosing:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Narxni o'zgartirish", callback_data="edit_price")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_settings")],
    ])

    await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# --- BOSHQA SOZLAMALAR ---
@router.callback_query(F.data == "admin_other")
async def admin_other_handler(callback: CallbackQuery):
    """Boshqa sozlamalar"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Sizda bu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    text = (
        "⚙️ *Boshqa Sozlamalar*\n\n"
        "👇 Qaysi parametrni o'zgartirmoqchisiz?"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔔 Xabarlar", callback_data="admin_notifications")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_settings")],
    ])

    await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# --- PLACEHOLDER HANDLERS ---
@router.callback_query(F.data == "edit_price")
async def edit_price_handler(callback: CallbackQuery, state: FSMContext):
    """Narxni o'zgartirish"""
    await state.set_state(AdminStates.waiting_for_link)  # Vaqtincha
    await callback.message.answer("💰 Yangi narxni so'ming birligida yuboring (masalan: 5000)")
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    """Statistika ko'rsatadi"""
    text = "📊 *Statistika*\n\n🔄 Tez orada..."
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_notifications")
async def admin_notifications_handler(callback: CallbackQuery):
    """Xabarlar sozlamalari"""
    text = "🔔 *Xabarlar Sozlamalari*\n\n🔄 Tez orada..."
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()
