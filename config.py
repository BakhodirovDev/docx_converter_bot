import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

if os.path.exists(".env.development"):
    load_dotenv(".env.development")
else:
    load_dotenv(".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FILE_PRICE = int(os.getenv("FILE_PRICE", "5000"))
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")

# Majburiy obuna kanali (@ belgisiz, masalan: oxu_docx_channel)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")  # .env ga qo'shish kerak

# PostgreSQL connection — passwordni URL-encode qilish
pg_user = os.getenv("POSTGRES_USER", "postgres")
pg_password = os.getenv("POSTGRES_PASSWORD", "")
pg_host = os.getenv("POSTGRES_HOST", "localhost")
pg_port = os.getenv("POSTGRES_PORT", "5432")
pg_db = os.getenv("POSTGRES_DB", "converter_bot")

# URL-encode password and user if necessary
pg_user_enc = quote_plus(pg_user)
pg_password_enc = quote_plus(pg_password)

DB_DSN = f"postgresql+asyncpg://{pg_user_enc}:{pg_password_enc}@{pg_host}:{pg_port}/{pg_db}"
