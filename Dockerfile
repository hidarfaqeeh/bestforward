# استخدام Python 3.11 كصورة أساسية (3.13 قد يسبب مشاكل)
FROM python:3.11-slim

# تعيين متغيرات البيئة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC
ENV PATH="/home/botuser/.local/bin:$PATH"

# تحديث النظام وتثبيت المتطلبات الأساسية
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مستخدم غير جذر
RUN useradd -m -s /bin/bash botuser

# تعيين مجلد العمل
WORKDIR /app

# نسخ requirements المؤقت لتحسين cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# نسخ ملفات المشروع
COPY --chown=botuser:botuser . .

# إنشاء مجلد للملفات المؤقتة والسجلات
RUN mkdir -p logs && \
    chmod 755 logs && \
    chown botuser:botuser logs

# التبديل إلى المستخدم غير الجذر
USER botuser

# تعريف المتغيرات الافتراضية
ENV BOT_TOKEN=""
ENV DATABASE_URL=""
ENV ADMIN_USER_IDS=""
ENV WEBHOOK_HOST=""
ENV WEBHOOK_PORT=5000

# كشف المنفذ
EXPOSE 5000

# فحص صحة التطبيق
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# تشغيل البوت
CMD ["python", "main.py"]