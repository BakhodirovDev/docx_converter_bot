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
from database.models import Base, User, Settings, Payment
from handlers.convert import convert_docx_to_txt
from handlers.admin import router as admin_router
from utils import ensure_dir, validate_docx, get_text

bot = Bot(BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(admin_router)

ensure_dir("files")

# Gruh fayllarni vaqtincha saqlash
pending_group_files = {}
# Gruh timeout tasklar
group_timeout_tasks = {}


@dp.message(CommandStart())
async def start(message: types.Message):
    async for session in get_session():
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        #  Agar foydalanuvchi oldin ro''yxatdan o''tgan bo''lsa
        if user and user.language:
            lang = user.language
            await send_main_menu(message, lang)
            return

        #  Agar yangi foydalanuvchi bo''lsa yoki tili yo''q bo''lsa
        lang_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=" O''zbek", callback_data="lang_uz"),
            InlineKeyboardButton(text=" Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text=" English", callback_data="lang_en")
        ]])
        await message.answer(
            "Tilni tanlang / Выберите язык / Choose language:",
            reply_markup=lang_kb
        )


# --- Tilni saqlash ---
@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]

    async for session in get_session():
        stmt = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                language=lang
            )
            session.add(user)
        else:
            user.language = lang
        await session.commit()

    await callback.answer()
    await send_main_menu(callback.message, lang)


async def send_main_menu(message: types.Message, lang: str):
    buttons = [
        [InlineKeyboardButton(text=get_text(lang, "convert_btn"), callback_data="start_convert")]
    ]

    # Faqat admin uchun tugma qo''shamiz
    if message.from_user.id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text=" Admin Sozlamalar", callback_data="admin_settings")])

    main_kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        f"{get_text(lang, 'start')}\n\n{get_text(lang, 'choose_action')}",
        reply_markup=main_kb
    )


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
    ])

    await callback.message.answer(get_text(lang, "offer_text"), reply_markup=kb)


# --- Faylni so''rash ---
@dp.callback_query(F.data == "confirm_offer")
async def ask_file(callback: types.CallbackQuery):
    async for session in get_session():
        stmt = select(User.language).where(User.telegram_id == callback.from_user.id)
        lang = (await session.execute(stmt)).scalar() or "uz"
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(" Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
