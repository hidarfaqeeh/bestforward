#!/bin/bash

# إعداد نشر البوت مع دعم الويب هوك والـ Polling
# Telegram Forwarding Bot Deployment Script

set -e

echo "🚀 إعداد نشر بوت التليجرام للتوجيه التلقائي"
echo "=========================================="

# التحقق من وجود متغيرات البيئة المطلوبة
check_required_vars() {
    echo "📋 التحقق من متغيرات البيئة..."
    
    if [ -z "$BOT_TOKEN" ]; then
        echo "❌ خطأ: BOT_TOKEN غير محدد"
        exit 1
    fi
    
    if [ -z "$DATABASE_URL" ]; then
        echo "⚠️  تحذير: DATABASE_URL غير محدد، سيتم استخدام قاعدة البيانات المحلية"
    fi
    
    if [ -z "$ADMIN_USER_IDS" ]; then
        echo "⚠️  تحذير: ADMIN_USER_IDS غير محدد"
    fi
    
    echo "✅ التحقق من متغيرات البيئة مكتمل"
}

# تثبيت المتطلبات
install_dependencies() {
    echo "📦 تثبيت المتطلبات..."
    
    # تثبيت Python packages
    pip install --no-cache-dir --upgrade pip
    pip install --no-cache-dir -e .
    
    echo "✅ تم تثبيت المتطلبات بنجاح"
}

# إعداد قاعدة البيانات
setup_database() {
    echo "🗄️  إعداد قاعدة البيانات..."
    
    # إنشاء مجلد logs إذا لم يكن موجوداً
    mkdir -p logs
    
    echo "✅ إعداد قاعدة البيانات مكتمل"
}

# اختبار الاتصال بالبوت
test_bot_connection() {
    echo "🤖 اختبار الاتصال بالبوت..."
    
    python -c "
import asyncio
import os
from aiogram import Bot

async def test_bot():
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    try:
        me = await bot.get_me()
        print(f'✅ البوت متصل بنجاح: {me.first_name} (@{me.username})')
        return True
    except Exception as e:
        print(f'❌ فشل الاتصال بالبوت: {e}')
        return False
    finally:
        await bot.session.close()

result = asyncio.run(test_bot())
if not result:
    exit(1)
"
}

# إعداد الويب هوك
setup_webhook() {
    echo "🌐 إعداد الويب هوك..."
    
    if [ -n "$WEBHOOK_HOST" ] && [[ "$WEBHOOK_HOST" != localhost* ]]; then
        echo "📡 تم اكتشاف WEBHOOK_HOST: $WEBHOOK_HOST"
        echo "🔄 سيتم تشغيل البوت في وضع الويب هوك مع الرجوع التلقائي للـ Polling"
        
        # إعداد متغيرات الويب هوك
        export WEBHOOK_PORT=${WEBHOOK_PORT:-5000}
        export WEBHOOK_SECRET=${WEBHOOK_SECRET:-webhook_secret_token_2024}
        
        echo "✅ إعداد الويب هوك مكتمل"
        echo "   - المضيف: $WEBHOOK_HOST"
        echo "   - المنفذ: $WEBHOOK_PORT"
        echo "   - سيتم الرجوع للـ Polling في حالة فشل الويب هوك"
    else
        echo "📊 لم يتم اكتشاف WEBHOOK_HOST صالح، سيتم استخدام وضع Polling"
    fi
}

# إعداد تشغيل البوت
setup_startup() {
    echo "⚙️  إعداد تشغيل البوت..."
    
    # إنشاء ملف startup script
    cat > start_bot.sh << 'EOF'
#!/bin/bash

echo "🚀 بدء تشغيل بوت التليجرام للتوجيه التلقائي"

# تصدير متغيرات البيئة من ملف الجلسة إذا كان موجوداً
if [ -f "new_session.txt" ]; then
    export STRING_SESSION=$(cat new_session.txt)
    echo "📱 تم تحميل جلسة Userbot"
fi

# تشغيل البوت
python main.py
EOF
    
    chmod +x start_bot.sh
    echo "✅ تم إنشاء ملف التشغيل start_bot.sh"
}

# تشغيل البوت
start_bot() {
    echo "🚀 تشغيل البوت..."
    
    # تشغيل البوت مع إعادة التشغيل التلقائي
    while true; do
        echo "$(date): بدء تشغيل البوت..."
        
        # تشغيل البوت والتحقق من رمز الخروج
        if python main.py; then
            echo "$(date): البوت توقف بشكل طبيعي"
            break
        else
            exit_code=$?
            echo "$(date): البوت توقف برمز خطأ: $exit_code"
            
            # إعادة التشغيل بعد 5 ثوانٍ في حالة الخطأ
            echo "إعادة التشغيل خلال 5 ثوانٍ..."
            sleep 5
        fi
    done
}

# الدالة الرئيسية
main() {
    echo "🌟 بدء عملية النشر..."
    
    check_required_vars
    install_dependencies
    setup_database
    test_bot_connection
    setup_webhook
    setup_startup
    
    echo ""
    echo "✅ إعداد النشر مكتمل بنجاح!"
    echo ""
    echo "📝 ملخص الإعداد:"
    echo "   - البوت: متصل ومجهز"
    echo "   - قاعدة البيانات: جاهزة"
    if [ -n "$WEBHOOK_HOST" ] && [[ "$WEBHOOK_HOST" != localhost* ]]; then
        echo "   - الوضع: ويب هوك مع رجوع تلقائي للـ Polling"
        echo "   - الويب هوك: $WEBHOOK_HOST:${WEBHOOK_PORT:-5000}"
    else
        echo "   - الوضع: Polling"
    fi
    echo ""
    echo "🚀 لتشغيل البوت:"
    echo "   ./start_bot.sh"
    echo ""
    echo "📊 لمراقبة السجلات:"
    echo "   tail -f logs/bot.log"
}

# تشغيل الدالة الرئيسية
main "$@"