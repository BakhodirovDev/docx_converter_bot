import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# .env yoki .env.development dan o‘qish
if os.path.exists(".env.development"):
    load_dotenv(".env.development")
else:
    load_dotenv(".env")

# PostgreSQL parametrlarini o‘qish
pg_user = os.getenv("POSTGRES_USER", "postgres")
pg_password = os.getenv("POSTGRES_PASSWORD", "")
pg_host = os.getenv("POSTGRES_HOST", "localhost")
pg_port = os.getenv("POSTGRES_PORT", "5432")
pg_db = os.getenv("POSTGRES_DB", "converter_bot")

# URL-encode user va parol (maxsus belgilar uchun)
pg_user_enc = quote_plus(pg_user)
pg_password_enc = quote_plus(pg_password)

# PostgreSQL DSN
DATABASE_URL = f"postgresql+asyncpg://{pg_user_enc}:{pg_password_enc}@{pg_host}:{pg_port}/{pg_db}"

# SQLAlchemy engine va session
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Session generator (dependency uchun)
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
