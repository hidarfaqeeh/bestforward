# دليل نشر بوت تيليجرام على Northflank

## المتطلبات الأساسية

### 1. إعداد البوت
1. إنشاء بوت جديد عبر [@BotFather](https://t.me/BotFather)
2. الحصول على `BOT_TOKEN`
3. الحصول على معرف المشرف (يمكن الحصول عليه من [@userinfobot](https://t.me/userinfobot))

### 2. إعداد قاعدة البيانات (اختياري للميزات المتقدمة)
- إعداد Telegram API credentials من [my.telegram.org](https://my.telegram.org)
- الحصول على `API_ID` و `API_HASH`

## خطوات النشر على Northflank

### 1. رفع الكود إلى GitHub
```bash
git add .
git commit -m "Initial bot setup"
git push origin main
```

### 2. إعداد Northflank Project

1. **إنشاء مشروع جديد:**
   - اذهب إلى [Northflank Dashboard](https://app.northflank.com)
   - أنشئ مشروع جديد
   - اختر "Build Service" → "Dockerfile"

2. **ربط GitHub Repository:**
   - اختر الـ repository الخاص بك
   - تأكد من أن الـ branch هو `main`
   - Path to Dockerfile: `./Dockerfile`

### 3. إعداد متغيرات البيئة

في صفحة Environment Variables، أضف:

#### متغيرات ضرورية:
```
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_USER_IDS=123456789,987654321
DATABASE_URL=sqlite:///data/telegram_bot.db
WEBHOOK_HOST=your-app-name.northflank.app
```

#### متغيرات اختيارية للميزات المتقدمة:
```
API_ID=your_api_id
API_HASH=your_api_hash
STRING_SESSION=your_session_string
ENCRYPTION_KEY=your-32-character-key
```

### 4. إعدادات المنافذ (Ports)
- **Port**: 5000
- **Protocol**: HTTP
- **Public**: مفعل

### 5. إعدادات الموارد
- **CPU**: 0.2 vCPU (قابل للزيادة حسب الحاجة)
- **Memory**: 512Mi (قابل للزيادة حسب الحاجة)
- **Storage**: 1GB ephemeral storage

### 6. نشر التطبيق
- اضغط على "Deploy"
- انتظر حتى تكتمل عملية البناء والنشر

## استخدام PostgreSQL (للاستخدام المكثف)

### 1. إنشاء قاعدة بيانات PostgreSQL
في Northflank:
1. أنشئ "Add-on" جديد
2. اختر "PostgreSQL"
3. اختر الخطة المناسبة

### 2. تحديث متغيرات البيئة
```
DATABASE_URL=postgresql://username:password@host:port/database
```

## اختبار النشر

### 1. فحص Health Check
```bash
curl https://your-app-name.northflank.app/health
```

### 2. فحص معلومات الـ Webhook
```bash
curl https://your-app-name.northflank.app/webhook-info
```

### 3. اختبار البوت
- أرسل `/start` للبوت
- تأكد من أن البوت يرد

## حل المشاكل الشائعة

### 1. خطأ "Bot not responding"
- تحقق من `BOT_TOKEN`
- تأكد من أن الـ webhook مضبوط صحيحاً
- فحص logs في Northflank

### 2. خطأ "Database connection failed"
- تحقق من `DATABASE_URL`
- تأكد من أن قاعدة البيانات متاحة

### 3. خطأ "Permission denied"
- تأكد من أن `ADMIN_USER_IDS` يحتوي على معرفك
- تحقق من أن المعرفات مفصولة بفواصل

## مراقبة التطبيق

### 1. Logs
- استخدم Northflank logs لمراقبة أداء البوت
- ابحث عن أخطاء في logs/bot.log

### 2. Metrics
- راقب استخدام CPU والذاكرة
- راقب عدد الطلبات والاستجابات

### 3. Health Checks
- تأكد من أن health checks تعمل بشكل صحيح
- اضبط تنبيهات للفشل

## الأمان

### 1. متغيرات البيئة
- لا تضع tokens في الكود
- استخدم Northflank Secrets للبيانات الحساسة

### 2. قاعدة البيانات
- استخدم SSL للاتصال بقاعدة البيانات
- قم بنسخ احتياطية منتظمة

### 3. Webhook Security
- استخدم HTTPS فقط
- اضبط webhook secret إذا أمكن

## تحديث البوت

### 1. تحديث الكود
```bash
git add .
git commit -m "Update bot features"
git push origin main
```

### 2. إعادة نشر على Northflank
- سيتم إعادة النشر تلقائياً عند push جديد
- راقب عملية البناء في dashboard

## النسخ الاحتياطية

### 1. قاعدة البيانات
- اضبط نسخ احتياطية منتظمة لقاعدة البيانات
- اختبر استعادة البيانات دورياً

### 2. الكود
- احتفظ بنسخة من الكود في GitHub
- استخدم tags للإصدارات المهمة

## الدعم والصيانة

### 1. مراقبة دورية
- تحقق من logs يومياً
- راقب استهلاك الموارد

### 2. تحديثات الأمان
- حدث التبعيات بانتظام
- راقب تحديثات الأمان

### 3. أداء البوت
- راقب سرعة الاستجابة
- حسن الكود حسب الحاجة