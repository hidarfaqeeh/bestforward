# استخدام Python 3.11 كصورة أساسية
FROM python:3.11-slim

# تعيين متغيرات البيئة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC

# تحديث النظام وتثبيت المتطلبات الأساسية
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مجلد العمل
WORKDIR /app

# نسخ ملفات المشروع
COPY . .

# تثبيت المتطلبات من pyproject.toml
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir .

# إنشاء مجلد للملفات المؤقتة والسجلات
RUN mkdir -p logs
RUN chmod 755 logs

# تعريف المتغيرات الافتراضية
ENV BOT_TOKEN=""
ENV DATABASE_URL=""
ENV ADMIN_USER_IDS=""
ENV WEBHOOK_HOST=""
ENV WEBHOOK_PORT=5000

# كشف المنفذ
EXPOSE 5000

# فحص صحة التطبيق
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; import asyncpg; asyncio.run(asyncpg.connect('${DATABASE_URL}').close())" || exit 1

# تشغيل البوت
CMD ["python", "main.py"]