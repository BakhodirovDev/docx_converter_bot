# Python 3.11 slim image
FROM python:3.11-slim

# Working directory
WORKDIR /app

# System dependencies (postgresql-client uchun)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application files
COPY . .

# Files directory yaratish
RUN mkdir -p /app/files

# Environment variables (ularni .env dan yoki docker-compose dan olinadi)
ENV PYTHONUNBUFFERED=1

# Bot ishga tushirish
CMD ["python", "main.py"]
