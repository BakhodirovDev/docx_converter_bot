from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime, Float, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    language = Column(String(3), nullable=True)
    is_admin = Column(Boolean, default=False)
    
    # Referral system
    referral_code = Column(String(20), unique=True, index=True, nullable=True)
    referred_by = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
    balance = Column(Float, default=0.0)
    total_earned = Column(Float, default=0.0)  # Jami ishlab topgan pul
    created_at = Column(DateTime, default=datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    uz_offer = Column(String)
    ru_offer = Column(String)
    en_offer = Column(String)
    referral_reward = Column(Float, default=1000.0)  # Referal mukofoti


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, index=True)
    invoice_id = Column(String, unique=True, index=True)
    file_name = Column(String)
    amount = Column(Float)
    payment_method = Column(String, default="click")  # click, balance
    status = Column(String, default="pending")  # pending, paid, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)


class ReferralHistory(Base):
    __tablename__ = "referral_history"
    id = Column(Integer, primary_key=True)
    referrer_id = Column(BigInteger, ForeignKey("users.telegram_id"), index=True)  # Kim taklif qilgan
    referred_id = Column(BigInteger, ForeignKey("users.telegram_id"), index=True)  # Kim kelgan
    reward_amount = Column(Float)  # Qancha pul berilgan
    created_at = Column(DateTime, default=datetime.utcnow)


class Promocode(Base):
    __tablename__ = "promocodes"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, index=True)  # Promokod
    reward_amount = Column(Float)  # Mukofot summasi
    max_uses = Column(Integer, default=1)  # Maksimal foydalanish soni
    current_uses = Column(Integer, default=0)  # Hozirgi foydalanish soni
    is_active = Column(Boolean, default=True)  # Faol yoki yo'q
    created_by = Column(BigInteger, ForeignKey("users.telegram_id"))  # Kim yaratgan (admin)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Amal qilish muddati


class PromocodeUsage(Base):
    __tablename__ = "promocode_usage"
    id = Column(Integer, primary_key=True)
    promocode_id = Column(Integer, ForeignKey("promocodes.id"), index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), index=True)
    reward_amount = Column(Float)
    used_at = Column(DateTime, default=datetime.utcnow)
