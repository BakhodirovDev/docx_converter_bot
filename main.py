import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from sqlalchemy.future import select
from config import BOT_TOKEN, PROVIDER_TOKEN, FILE_PRICE, ADMIN_ID
from database.db import get_session, engine
from database.models import Base, User, Settings, Payment, ReferralHistory
from handlers.convert import convert_docx_to_txt
from handlers.admin import router as admin_router
from handlers.referral import generate_referral_code, extract_referral_code
from utils import ensure_dir, validate_docx, get_text

bot = Bot(BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(admin_router)

ensure_dir("files")

# Bot ma'lumotlari (username uchun)
BOT_INFO = None

# Gruh fayllarni vaqtincha saqlash
pending_group_files = {}
# Gruh timeout tasklar
group_timeout_tasks = {}


@dp.message(CommandStart())
async def start(message: types.Message):
    # Referal kodni ajratib olish
    referral_code = extract_referral_code(message.text)
    
    async for session in get_session():
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        # Agar foydalanuvchi oldin ro'yxatdan o'tgan bo'lsa
        if user and user.language:
            lang = user.language
            await send_main_menu(message, lang)
            return

        # Yangi foydalanuvchi - referal kodni tekshirish
        referred_by_id = None
        if referral_code:
            # Referal kod egasini topish
            ref_stmt = select(User).where(User.referral_code == referral_code)
            ref_result = await session.execute(ref_stmt)
            referrer = ref_result.scalar_one_or_none()
            
            if referrer and referrer.telegram_id != message.from_user.id:
                referred_by_id = referrer.telegram_id

        # Agar yangi foydalanuvchi bo'lsa yoki tili yo'q bo'lsa
        lang_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data=f"lang_uz_{referred_by_id or 0}"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"lang_ru_{referred_by_id or 0}"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data=f"lang_en_{referred_by_id or 0}")
        ]])
        await message.answer(
            "Tilni tanlang / Выберите язык / Choose language:",
            reply_markup=lang_kb
        )


# --- Tilni saqlash ---
@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    lang = parts[1]
    referred_by_id = int(parts[2]) if len(parts) > 2 else 0

    async for session in get_session():
        stmt = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Yangi foydalanuvchi - referal kod yaratish
            new_referral_code = generate_referral_code()
            
            # Unique ekanligini tekshirish
            while True:
                check_stmt = select(User).where(User.referral_code == new_referral_code)
                check_result = await session.execute(check_stmt)
                if not check_result.scalar_one_or_none():
                    break
                new_referral_code = generate_referral_code()
            
            user = User(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                language=lang,
                referral_code=new_referral_code,
                referred_by=referred_by_id if referred_by_id != 0 else None
            )
            session.add(user)
            await session.commit()
            
            # Agar referal orqali kelgan bo'lsa - mukofot berish
            if referred_by_id and referred_by_id != 0:
                # Settings dan referal mukofot summasini olish
                settings_stmt = select(Settings).limit(1)
                settings = (await session.execute(settings_stmt)).scalar_one_or_none()
                reward = settings.referral_reward if settings else 1000.0
                
                # Referer ga pul qo'shish
                referrer_stmt = select(User).where(User.telegram_id == referred_by_id)
                referrer_result = await session.execute(referrer_stmt)
                referrer = referrer_result.scalar_one_or_none()
                
                if referrer:
                    referrer.balance += reward
                    referrer.total_earned += reward
                    
                    # ReferralHistory ga yozish
                    ref_history = ReferralHistory(
                        referrer_id=referred_by_id,
                        referred_id=callback.from_user.id,
                        reward_amount=reward
                    )
                    session.add(ref_history)
                    await session.commit()
                    
                    # Referrer ga xabar yuborish
                    try:
                        await bot.send_message(
                            referred_by_id,
                            f"🎉 Yangi foydalanuvchi sizning havolangiz orqali qo'shildi!\n"
                            f"💰 Balansingizga +{reward:,.0f} UZS qo'shildi"
                        )
                    except:
                        pass
        else:
            user.language = lang
            await session.commit()

    await callback.answer()
    await send_main_menu(callback.message, lang)


async def send_main_menu(message: types.Message, lang: str):
    buttons = [
        [InlineKeyboardButton(text=get_text(lang, "convert_btn"), callback_data="start_convert")],
        [InlineKeyboardButton(text=get_text(lang, "referral_btn"), callback_data="my_referral")],
        [InlineKeyboardButton(text=get_text(lang, "profile_btn"), callback_data="my_profile")]
    ]

    # Faqat admin uchun tugma qo'shamiz
    if message.from_user.id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="admin_settings")])

    main_kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        f"{get_text(lang, 'start')}\n\n{get_text(lang, 'choose_action')}",
        reply_markup=main_kb
    )


# --- Profil ko'rsatish ---
@dp.callback_query(F.data == "my_profile")
async def show_profile(callback: types.CallbackQuery):
    async for session in get_session():
        stmt = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
            return
        
        lang = user.language or "uz"
        
        # Referal statistikasi
        from sqlalchemy import func
        ref_count_stmt = select(func.count(User.id)).where(User.referred_by == user.telegram_id)
        ref_count = (await session.execute(ref_count_stmt)).scalar() or 0
        
        profile_text = get_text(lang, "profile_text").format(
            name=user.first_name or "User",
            username=f"@{user.username}" if user.username else "—",
            balance=user.balance or 0,
            total_earned=user.total_earned or 0,
            referrals=ref_count,
            ref_code=user.referral_code or "—"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 " + get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(profile_text, reply_markup=kb, parse_mode="HTML")
        except:
            await callback.message.answer(profile_text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()


# --- Referal havolani ko'rsatish ---
@dp.callback_query(F.data == "my_referral")
async def show_referral(callback: types.CallbackQuery):
    global BOT_INFO
    
    async for session in get_session():
        stmt = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
            return
        
        lang = user.language or "uz"
        
        # Referal statistikasi
        from sqlalchemy import func
        ref_count_stmt = select(func.count(User.id)).where(User.referred_by == user.telegram_id)
        ref_count = (await session.execute(ref_count_stmt)).scalar() or 0
        
        # Settings dan referal mukofotini olish
        settings_stmt = select(Settings).limit(1)
        settings = (await session.execute(settings_stmt)).scalar_one_or_none()
        reward = settings.referral_reward if settings else 1000.0
        
        # Bot username olish (cache qilish)
        if not BOT_INFO:
            BOT_INFO = await bot.get_me()
        
        ref_link = f"https://t.me/{BOT_INFO.username}?start={user.referral_code}"
        
        referral_text = get_text(lang, "referral_text").format(
            link=ref_link,
            reward=f"{reward:,.0f}",
            count=ref_count,
            earned=f"{user.total_earned or 0:,.0f}"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 " + get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(referral_text, reply_markup=kb, parse_mode="HTML")
        except:
            await callback.message.answer(referral_text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()


# --- Asosiy menyuga qaytish ---
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    async for session in get_session():
        stmt = select(User.language).where(User.telegram_id == callback.from_user.id)
        lang = (await session.execute(stmt)).scalar() or "uz"
    
    # Menyuni edit qilamiz
    buttons = [
        [InlineKeyboardButton(text=get_text(lang, "convert_btn"), callback_data="start_convert")],
        [InlineKeyboardButton(text=get_text(lang, "referral_btn"), callback_data="my_referral")],
        [InlineKeyboardButton(text=get_text(lang, "profile_btn"), callback_data="my_profile")]
    ]

    # Faqat admin uchun tugma qo'shamiz
    if callback.from_user.id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="admin_settings")])

    main_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(
            f"{get_text(lang, 'start')}\n\n{get_text(lang, 'choose_action')}",
            reply_markup=main_kb
        )
    except:
        await callback.message.answer(
            f"{get_text(lang, 'start')}\n\n{get_text(lang, 'choose_action')}",
            reply_markup=main_kb
        )
    await callback.answer()


# --- Ommaviy oferta ---
@dp.callback_query(F.data == "start_convert")
async def confirm_offer(callback: types.CallbackQuery):
    async for session in get_session():
        user_lang_stmt = select(User.language).where(User.telegram_id == callback.from_user.id)
        lang = (await session.execute(user_lang_stmt)).scalar() or "uz"

        settings_stmt = select(Settings).limit(1)
        settings = (await session.execute(settings_stmt)).scalar_one_or_none()

    offer_url = get_offer_link(lang, settings)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "view_offer"), url=offer_url)],
        [InlineKeyboardButton(text=get_text(lang, "confirm"), callback_data="confirm_offer")],
        [InlineKeyboardButton(text="🏠 " + get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
    ])

    try:
        await callback.message.edit_text(get_text(lang, "offer_text"), reply_markup=kb)
    except:
        await callback.message.answer(get_text(lang, "offer_text"), reply_markup=kb)
    await callback.answer()


# --- Faylni so''rash ---
@dp.callback_query(F.data == "confirm_offer")
async def ask_file(callback: types.CallbackQuery):
    async for session in get_session():
        stmt = select(User.language).where(User.telegram_id == callback.from_user.id)
        lang = (await session.execute(stmt)).scalar() or "uz"
    
    await callback.answer()
    await callback.message.answer(get_text(lang, "send_file"))


# --- Faylni qabul qilish ---
@dp.message(F.document)
async def handle_file(message: types.Message):
    async for session in get_session():
        stmt = select(User.language).where(User.telegram_id == message.from_user.id)
        lang = (await session.execute(stmt)).scalar() or "uz"

    doc = message.document
    if not validate_docx(doc.file_name):
        await message.answer(get_text(lang, "not_docx"))
        return

    file_path = f"files/{message.from_user.id}_{doc.file_name}"
    
    try:
        # Faylni yuklab olish
        file_info = await bot.get_file(doc.file_id)
        await bot.download_file(file_info.file_path, destination=file_path)

        # Gruh yoki bitta fayl
        user_id = message.from_user.id
        
        # Agar gruh bo'lsa group_id ishlatish, aks holda user_id ishlatish
        if message.media_group_id:
            group_id = message.media_group_id
            key = f"{user_id}_{group_id}"
        else:
            # Bitta fayl - fake "group" yaratish (timeout keyin invoice yubor)
            group_id = f"single_{message.message_id}"
            key = f"{user_id}_{group_id}"
        
        if key not in pending_group_files:
            pending_group_files[key] = {
                "files": [],
                "total_price": 0,
                "lang": lang,
                "chat_id": message.chat.id
            }
            # Eski taskni bekor qilish
            if key in group_timeout_tasks and not group_timeout_tasks[key].done():
                group_timeout_tasks[key].cancel()
        
        pending_group_files[key]["files"].append(file_path)
        pending_group_files[key]["total_price"] += FILE_PRICE
        
        file_count = len(pending_group_files[key]["files"])
        await message.answer(f"📁 Fayl qabul qilindi ({file_count}/...)")
        
        # Timeout - 3 sekund kutib, yangi fayl kelmasa invoice yubor
        async def process_group_after_delay():
            try:
                await asyncio.sleep(3.0)  # 3 sekund kutish
                if key in pending_group_files:
                    await send_group_invoice(key, lang)
            except asyncio.CancelledError:
                pass  # Task bekor qilindi, yangi fayllar kelmoqda
            except Exception as e:
                print(f"Gruh timeout xatosi: key={key}, error={type(e).__name__}: {e}")
        
        # Eski taskni bekor qilish (yangi fayllar kelmoqda)
        if key in group_timeout_tasks and not group_timeout_tasks[key].done():
            group_timeout_tasks[key].cancel()
        
        # Yangi task yaratish
        task = asyncio.create_task(process_group_after_delay())
        group_timeout_tasks[key] = task
            
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


async def send_group_invoice(key: str, lang: str):
    """Gruh fayllar uchun birlashtirilgan invoice yuboradi"""
    import json
    import uuid
    
    data = pending_group_files.get(key)
    if not data:
        return
    
    try:
        file_count = len(data["files"])
        total_price = data["total_price"]
        
        # Invoice ID yaratish
        invoice_id = str(uuid.uuid4())
        
        # Invoice ID ni data ga qo'shish (keyinchalik topish uchun)
        data["invoice_id"] = invoice_id
        
        # JSON payload (128 bayt chegarasida)
        payload = json.dumps({
            "invoice_id": invoice_id,
            "is_group": True,
            "count": file_count
        })
        
        prices = [LabeledPrice(label=f"{file_count}ta fayl", amount=total_price * 100)]
        
        if not PROVIDER_TOKEN:
            raise ValueError("PROVIDER_TOKEN is not configured in .env file")
        
        await bot.send_invoice(
            chat_id=data["chat_id"],
            title=get_text(lang, "payment_title"),
            description=f"{file_count}ta fayl konvertatsiyasi",
            provider_token=PROVIDER_TOKEN,
            currency="UZS",
            prices=prices,
            payload=payload
        )
        
        # Payment recordini database ga saqlash
        try:
            user_id_str = key.split("_")[0]
            telegram_id = int(user_id_str)
            
            async for session in get_session():
                payment = Payment(
                    telegram_id=telegram_id,
                    invoice_id=invoice_id,
                    file_name=f"{file_count} files",
                    amount=total_price,
                    status="pending"
                )
                session.add(payment)
                await session.commit()
        except (ValueError, IndexError) as e:
            print(f"Payment save error: key={key}, error={e}")
    except Exception as e:
        print(f"Invoice yuborishda xatolik: {type(e).__name__}: {e}")
        # Faqat error bo'lsa pending groupni o'chirish
        if key in pending_group_files:
            del pending_group_files[key]
        if key in group_timeout_tasks:
            del group_timeout_tasks[key]


@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    import json
    
    payload_str = message.successful_payment.invoice_payload
    
    async for session in get_session():
        stmt = select(User.language).where(User.telegram_id == message.from_user.id)
        lang = (await session.execute(stmt)).scalar() or "uz"

    try:
        # Payload ni parse qilish
        payload = json.loads(payload_str)
        invoice_id = payload.get("invoice_id")
        
        # Invoice holati tekshirish - duplicate payment oldini olish
        async for session in get_session():
            stmt = select(Payment).where(Payment.invoice_id == invoice_id)
            result = await session.execute(stmt)
            payment = result.scalar_one_or_none()
            
            if payment and payment.status == "paid":
                await message.answer("⚠️ Bu invoice allaqachon to'langan!")
                return
            
            if payment:
                payment.status = "paid"
                payment.paid_at = datetime.now()
                await session.commit()
        
        await message.answer(get_text(lang, "paid"))
        
        # Invoice_id bo'yicha pending_group_files dan fayllarni topish
        files_to_convert = []
        key_to_delete = None
        
        for key, group_data in list(pending_group_files.items()):
            if group_data.get("invoice_id") == invoice_id:
                files_to_convert = group_data.get("files", [])
                key_to_delete = key
                break
        
        if files_to_convert:
            # Fayllarni konvertatsiya qilish
            await message.answer(f"📦 {len(files_to_convert)}ta fayl tayyorlanmoqda...")
            
            for file_path in files_to_convert:
                try:
                    txt_path = file_path.replace(".docx", ".txt")
                    result_path = convert_docx_to_txt(file_path, txt_path)
                    await message.answer_document(types.FSInputFile(result_path))
                except Exception as e:
                    await message.answer(f"❌ Xatolik: {file_path} - {e}")
            
            # Pending groupni tozalash
            if key_to_delete:
                if key_to_delete in pending_group_files:
                    del pending_group_files[key_to_delete]
                if key_to_delete in group_timeout_tasks:
                    del group_timeout_tasks[key_to_delete]
        
        await message.answer(get_text(lang, "done"))
        
    except json.JSONDecodeError:
        # Eski format (faqat fayl path) uchun
        await message.answer(get_text(lang, "paid"))
        txt_path = payload_str.replace(".docx", ".txt")
        try:
            result_path = convert_docx_to_txt(payload_str, txt_path)
            await message.answer_document(types.FSInputFile(result_path))
            await message.answer(get_text(lang, "done"))
        except Exception as e:
            await message.answer(f"{get_text(lang, 'error')} {e}")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


def get_offer_link(lang: str, settings: Settings | None) -> str:
    if not settings:
        return "https://t.me/oxu_docx"
    return {
        "uz": settings.uz_offer,
        "ru": settings.ru_offer,
        "en": settings.en_offer,
    }.get(lang, settings.uz_offer)


async def main():
    global BOT_INFO
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Bot ma'lumotlarini olish
    BOT_INFO = await bot.get_me()
    print(f"✅ Bot ishga tushdi... (@{BOT_INFO.username})")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())