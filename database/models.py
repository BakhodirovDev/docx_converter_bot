from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime, Float
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
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


class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    uz_offer = Column(String)
    ru_offer = Column(String)
    en_offer = Column(String)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, index=True)
    invoice_id = Column(String, unique=True, index=True)
    file_name = Column(String)
    amount = Column(Float)
    status = Column(String, default="pending")  # pending, paid, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)