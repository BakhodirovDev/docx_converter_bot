import string
import random
from datetime import datetime
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.future import select
from database.db import get_session
from database.models import Promocode, PromocodeUsage, User
from utils import get_text
from config import ADMIN_ID

router = Router()


class PromoStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_amount = State()
    waiting_for_uses = State()
    entering_promo = State()


def generate_promo_code(length=8):
    """Tasodifiy promokod yaratish"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


# --- User promokod kiritish ---
@router.callback_query(F.data == "enter_promo")
async def ask_promo_code(callback: types.CallbackQuery, state: FSMContext):
    async for session in get_session():
        stmt = select(User.language).where(User.telegram_id == callback.from_user.id)
        lang = (await session.execute(stmt)).scalar() or "uz"
    
    await state.set_state(PromoStates.entering_promo)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 " + get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
    ])
    
    try:
        await callback.message.edit_text(get_text(lang, "promo_enter"), reply_markup=kb, parse_mode="HTML")
    except:
        await callback.message.answer(get_text(lang, "promo_enter"), reply_markup=kb, parse_mode="HTML")
    
    await callback.answer()


@router.message(PromoStates.entering_promo)
async def process_promo_code(message: types.Message, state: FSMContext):
    async for session in get_session():
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        lang = user.language if user else "uz"
        
        promo_code = message.text.strip().upper()
        
        # Promokodni topish
        promo_stmt = select(Promocode).where(
            Promocode.code == promo_code,
            Promocode.is_active == True
        )
        promo_result = await session.execute(promo_stmt)
        promo = promo_result.scalar_one_or_none()
        
        if not promo:
            await message.answer(get_text(lang, "promo_invalid"))
            return
        
        # Foydalanuvchi allaqachon ishlatganmi tekshirish
        usage_stmt = select(PromocodeUsage).where(
            PromocodeUsage.promocode_id == promo.id,
            PromocodeUsage.user_id == message.from_user.id
        )
        usage_result = await session.execute(usage_stmt)
        usage = usage_result.scalar_one_or_none()
        
        if usage:
            await message.answer(get_text(lang, "promo_used"))
            return
        
        # Limit tekshirish
        if promo.max_uses > 0 and promo.current_uses >= promo.max_uses:
            await message.answer(get_text(lang, "promo_limit"))
            return
        
        # Promokodni qo'llash
        user.balance += promo.reward_amount
        promo.current_uses += 1
        
        # Foydalanish tarixini saqlash
        usage = PromocodeUsage(
            promocode_id=promo.id,
            user_id=message.from_user.id,
            reward_amount=promo.reward_amount
        )
        session.add(usage)
        await session.commit()
        
        await message.answer(
            get_text(lang, "promo_success").format(
                amount=promo.reward_amount,
                code=promo_code
            ),
            parse_mode="HTML"
        )
        
        await state.clear()


# --- Admin promokod yaratish ---
@router.callback_query(F.data == "admin_create_promo")
async def start_create_promo(callback: types.CallbackQuery, state: FSMContext):
    async for session in get_session():
        stmt = select(User.language).where(User.telegram_id == callback.from_user.id)
        lang = (await session.execute(stmt)).scalar() or "uz"
    
    await state.set_state(PromoStates.waiting_for_code)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Avtomatik", callback_data="promo_auto_code")],
        [InlineKeyboardButton(text="🏠 " + get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
    ])
    
    try:
        await callback.message.edit_text(get_text(lang, "promo_create_code"), reply_markup=kb)
    except:
        await callback.message.answer(get_text(lang, "promo_create_code"), reply_markup=kb)
    
    await callback.answer()


@router.callback_query(F.data == "promo_auto_code", PromoStates.waiting_for_code)
async def auto_generate_code(callback: types.CallbackQuery, state: FSMContext):
    # Avtomatik kod yaratish
    promo_code = generate_promo_code()
    await state.update_data(code=promo_code)
    await state.set_state(PromoStates.waiting_for_amount)
    
    async for session in get_session():
        stmt = select(User.language).where(User.telegram_id == callback.from_user.id)
        lang = (await session.execute(stmt)).scalar() or "uz"
    
    await callback.message.answer(
        f"📝 Kod avtomatik yaratildi: <code>{promo_code}</code>\n\n" + get_text(lang, "promo_create_amount"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(PromoStates.waiting_for_code)
async def receive_promo_code(message: types.Message, state: FSMContext):
    promo_code = message.text.strip().upper()
    
    # Kod allaqachon mavjudligini tekshirish
    async for session in get_session():
        stmt = select(Promocode).where(Promocode.code == promo_code)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            await message.answer("❌ Bu kod allaqachon mavjud. Boshqa kod kiriting:")
            return
        
        lang_stmt = select(User.language).where(User.telegram_id == message.from_user.id)
        lang = (await session.execute(lang_stmt)).scalar() or "uz"
    
    await state.update_data(code=promo_code)
    await state.set_state(PromoStates.waiting_for_amount)
    await message.answer(get_text(lang, "promo_create_amount"))


@router.message(PromoStates.waiting_for_amount)
async def receive_promo_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
        
        await state.update_data(amount=amount)
        await state.set_state(PromoStates.waiting_for_uses)
        
        async for session in get_session():
            stmt = select(User.language).where(User.telegram_id == message.from_user.id)
            lang = (await session.execute(stmt)).scalar() or "uz"
        
        await message.answer(get_text(lang, "promo_create_uses"))
    except ValueError:
        await message.answer("❌ Noto'g'ri summa. Raqam kiriting:")


@router.message(PromoStates.waiting_for_uses)
async def receive_promo_uses(message: types.Message, state: FSMContext):
    try:
        max_uses = int(message.text.strip())
        if max_uses < 0:
            raise ValueError
        
        data = await state.get_data()
        code = data['code']
        amount = data['amount']
        
        # Promokodni saqlash
        async for session in get_session():
            promo = Promocode(
                code=code,
                reward_amount=amount,
                max_uses=max_uses if max_uses > 0 else 999999,  # 0 = cheksiz
                created_by=message.from_user.id
            )
            session.add(promo)
            await session.commit()
            
            lang_stmt = select(User.language).where(User.telegram_id == message.from_user.id)
            lang = (await session.execute(lang_stmt)).scalar() or "uz"
        
        uses_text = f"{max_uses}" if max_uses > 0 else "♾️ Cheksiz"
        
        await message.answer(
            get_text(lang, "promo_created").format(
                code=code,
                amount=amount,
                uses=uses_text
            ),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Noto'g'ri son. Raqam kiriting:")


# --- Admin promokodlar ro'yxati ---
@router.callback_query(F.data == "admin_promo_list")
async def show_promo_list(callback: types.CallbackQuery):
    async for session in get_session():
        stmt = select(Promocode).order_by(Promocode.created_at.desc()).limit(10)
        result = await session.execute(stmt)
        promos = result.scalars().all()
        
        lang_stmt = select(User.language).where(User.telegram_id == callback.from_user.id)
        lang = (await session.execute(lang_stmt)).scalar() or "uz"
        
        if not promos:
            await callback.message.edit_text(get_text(lang, "promo_list_empty"))
            await callback.answer()
            return
        
        text = "📋 <b>Promokodlar ro'yxati</b>\n\n"
        
        for promo in promos:
            status = "✅ Faol" if promo.is_active else "❌ Nofaol"
            max_uses_text = f"{promo.max_uses}" if promo.max_uses < 999999 else "♾️"
            text += f"📝 <code>{promo.code}</code>\n"
            text += f"💰 {promo.reward_amount:,.0f} UZS\n"
            text += f"👥 {promo.current_uses}/{max_uses_text}\n"
            text += f"{status}\n\n"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 " + get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        
    await callback.answer()
