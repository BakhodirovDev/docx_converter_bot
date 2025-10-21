# 📄 DOCX Converter Bot

Telegram bot orqali DOCX fayllarni TXT formatiga konvertatsiya qilish va test savol-javoblarini formatlash uchun professional yechim.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## 🌟 Xususiyatlar

- ✅ **DOCX → TXT konvertatsiya** - Jadvallardan savol-javoblarni ekstraktlash
- 💰 **Telegram Payments** - UZClick orqali to'lov qabul qilish
- 🌐 **Ko'p tilli interfeys** - O'zbek, Rus, Ingliz tillari
- 👥 **Guruh fayl yuklash** - Bir nechta faylni bitta to'lov bilan
- 🔒 **Takroriy to'lovlarni oldini olish** - Invoice status tracking
- 👨‍💼 **Admin panel** - Narx, oferta va sozlamalarni boshqarish
- 🐳 **Docker support** - Production deployment uchun tayyor
- 🚀 **Jenkins CI/CD** - Avtomatik deployment pipeline

## 📋 Texnik Stack

| Texnologiya | Versiya | Maqsad |
|------------|---------|--------|
| Python | 3.11+ | Asosiy backend |
| aiogram | 3.x | Telegram Bot Framework |
| PostgreSQL | 15 | Database |
| SQLAlchemy | 2.x | ORM (async) |
| python-docx | - | DOCX fayl processing |
| Docker | - | Containerization |
| Jenkins | - | CI/CD Pipeline |

## 🚀 Tezkor Boshlash

### 1. Repozitoriyani klonlash

```bash
git clone git@github.com:BakhodirovDev/docx_converter_bot.git
cd docx_converter_bot
```

### 2. Virtual environment yaratish

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# yoki
.venv\Scripts\activate  # Windows
```

### 3. Dependencies o'rnatish

```bash
pip install -r requirements.txt
```

### 4. Environment o'rnatish

`.env` fayl yarating va quyidagi ma'lumotlarni kiriting:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_from_@BotFather
PROVIDER_TOKEN=your_provider_token_from_@BotFather
ADMIN_ID=your_telegram_user_id

# Pricing
FILE_PRICE=5000

# PostgreSQL
POSTGRES_USER=docx_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=docx_converter_bot
```

### 5. PostgreSQL o'rnatish

**Docker bilan:**
```bash
docker run -d \
  --name docx-postgres \
  -e POSTGRES_USER=docx_user \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=docx_converter_bot \
  -p 5432:5432 \
  postgres:15-alpine
```

**Yoki local PostgreSQL:**
```bash
createdb -U postgres docx_converter_bot
```

### 6. Botni ishga tushirish

```bash
python main.py
```

Bot ishga tushganidan keyin `/start` komandasini yuboring! ✅

## 🐳 Docker bilan ishga tushirish

### docker-compose orqali

```bash
# .env faylni yarating (yuqoridagi namuna)

# Build va ishga tushirish
docker-compose up -d

# Loglarni ko'rish
docker-compose logs -f bot

# To'xtatish
docker-compose down
```

### Manual Docker

```bash
# Network yaratish
docker network create docx_network

# PostgreSQL
docker run -d \
  --name docx-postgres \
  --network docx_network \
  -e POSTGRES_USER=docx_user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=docx_converter_bot \
  postgres:15-alpine

# Bot
docker build -t docx-bot .
docker run -d \
  --name docx-converter-bot \
  --network docx_network \
  --env-file .env \
  -v $(pwd)/files:/app/files \
  docx-bot
```

## 🏗️ Loyiha Strukturasi

```
docx_converter_bot/
├── main.py                 # Asosiy bot file (dispatcher)
├── config.py               # Environment va config
├── utils.py                # Yordamchi funksiyalar
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image config
├── docker-compose.yml      # Multi-container orchestration
├── Jenkinsfile             # CI/CD pipeline
├── .dockerignore           # Docker build exclusions
├── .gitignore              # Git exclusions
├── database/
│   ├── db.py              # Database session management
│   └── models.py          # SQLAlchemy models (User, Settings, Payment)
├── handlers/
│   ├── admin.py           # Admin panel FSM handlers
│   └── convert.py         # DOCX → TXT konvertatsiya logikasi
├── locale/
│   ├── uz.json            # O'zbek tili matinlari
│   ├── ru.json            # Rus tili matinlari
│   └── en.json            # Ingliz tili matinlari
└── files/                 # Yuklangan va konvertatsiya qilingan fayllar
```

## 📊 Database Schema

### `users` jadvali
```sql
- id (SERIAL PRIMARY KEY)
- telegram_id (BIGINT UNIQUE)
- username (VARCHAR)
- first_name (VARCHAR)
- last_name (VARCHAR)
- language (VARCHAR) -- uz/ru/en
- created_at (TIMESTAMP)
```

### `settings` jadvali
```sql
- id (SERIAL PRIMARY KEY)
- uz_offer (TEXT) -- O'zbek oferta URL
- ru_offer (TEXT) -- Rus oferta URL
- en_offer (TEXT) -- Ingliz oferta URL
- file_price (INTEGER) -- Fayl narxi
- boshqa_sozlamalar (TEXT) -- Qo'shimcha sozlamalar
```

### `payments` jadvali
```sql
- id (SERIAL PRIMARY KEY)
- telegram_id (BIGINT)
- invoice_id (VARCHAR UNIQUE) -- UUID
- file_name (VARCHAR)
- amount (FLOAT)
- status (VARCHAR) -- pending/paid/failed
- created_at (TIMESTAMP)
- paid_at (TIMESTAMP)
```

## 🔄 Konvertatsiya Logikasi

Bot DOCX fayldagi **jadvallarni** o'qib, quyidagi formatda TXT yaratadi:

### Input (DOCX jadvali):
| Savol | To'g'ri javob | Noto'g'ri 1 | Noto'g'ri 2 |
|-------|---------------|-------------|-------------|
| Pythonda list yaratish? | `my_list = []` | `my_list = {}` | `my_list = ()` |

### Output (TXT fayl):
```
? Pythonda list yaratish?
+ my_list = []
- my_list = {}
- my_list = ()

```

**Format qoidalari:**
- `?` - Savol
- `+` - To'g'ri javob (birinchi ustun)
- `-` - Noto'g'ri javoblar (qolgan ustunlar)

## 💳 To'lov Tizimi

### Guruh fayl yuklash
1. Foydalanuvchi **bir nechta fayl** yuboradi (media_group)
2. Bot **3 sekund** kutadi (qo'shimcha fayllar uchun)
3. **Bitta invoice** yaratiladi: `N ta fayl - XXXXX UZS`
4. To'lovdan keyin **barcha fayllar** konvertatsiya qilinadi

### Takroriy to'lovlar
- Har bir invoice `UUID` bilan identifikatsiya qilinadi
- `payments` jadvalida `status` tracking
- To'langan invoice qayta to'lanmaydi ✅

## 👨‍💼 Admin Panel

Admin panel FSM (Finite State Machine) bilan ishlaydi:

```
Admin Sozlamalar
├── 📝 Oferta
│   ├── O'zbek oferta URL
│   ├── Rus oferta URL
│   └── Ingliz oferta URL
├── 💰 Narx
│   └── Fayl narxini o'zgartirish
└── ⚙️ Boshqa Sozlamalar
    └── Maxsus konfiguratsiya
```

**Faqat `ADMIN_ID` ga ega foydalanuvchi** admin panelga kirishi mumkin.

## 🚀 Jenkins Deployment

### 1. Jenkins Credentials qo'shish:
```
Credentials → Add Credentials → Secret text:
- ID: docx-bot-token
- ID: docx-provider-token
- ID: docx-admin-id
- ID: docx-postgres-password
```

### 2. Pipeline yaratish:
```
New Item → Pipeline
SCM: Git
Repository: git@github.com:BakhodirovDev/docx_converter_bot.git
Branch: master
Script Path: Jenkinsfile
```

### 3. Deploy jarayoni:
```bash
1. Code push → GitHub
2. Jenkins → Build Now
3. Checkout → Build → Deploy → Verify
4. Bot ready! ✅
```

## 📝 Development

### Local ishga tushirish:
```bash
# Database migration (avtomatik)
python main.py  # Base.metadata.create_all

# Test qilish
# 1. Botga /start yuboring
# 2. Tilni tanlang
# 3. Fayl yuboring
# 4. To'lov qiling (test mode)
# 5. TXT faylni oling
```

### Yangi til qo'shish:
1. `locale/uz.json` ni nusxa oling → `locale/xx.json`
2. Barcha matnlarni tarjima qiling
3. `main.py` da til tugmasini qo'shing:
   ```python
   InlineKeyboardButton(text="🇽🇽 Yangi til", callback_data="lang_xx")
   ```

### Konvertatsiya logikasini o'zgartirish:
`handlers/convert.py` faylini tahrirlang:
```python
def extract_questions_and_answers(docx_file):
    # Sizning custom logika
    pass
```

## 🐛 Troubleshooting

### Bot ishga tushmayapti
```bash
# Loglarni tekshiring
docker logs docx-converter-bot

# Database connection test
docker exec -it docx-postgres psql -U docx_user -d docx_converter_bot
```

### Konvertatsiya ishlamayapti
```bash
# Python-docx test
python -c "from docx import Document; print('OK')"

# Fayl mavjudligini tekshiring
ls -la files/
```

### To'lov qabul qilmayapti
- `PROVIDER_TOKEN` to'g'riligini tekshiring
- @BotFather da to'lovlar yoqilganligini tasdiqlang
- UZS currency support borligini tekshiring

## 📜 License

MIT License - [LICENSE](LICENSE) faylini ko'ring

## 🤝 Hissa qo'shish

1. Fork qiling
2. Feature branch yarating: `git checkout -b feature/AmazingFeature`
3. Commit qiling: `git commit -m 'Add AmazingFeature'`
4. Push qiling: `git push origin feature/AmazingFeature`
5. Pull Request oching

## 📧 Contact

Developer: [@BakhodirovDev](https://github.com/BakhodirovDev)

Project Link: [https://github.com/BakhodirovDev/docx_converter_bot](https://github.com/BakhodirovDev/docx_converter_bot)

---

⭐ Agar loyiha foydali bo'lsa, **star** qo'yishni unutmang!
