# نظام بلوكتشين بي تو بي لبنك المرآة

نظام لامركزي لسلسلة الكتل (بلوكتشين) يستقبل المعاملات البنكية من نظام بنك المرآة ويسجلها في دفتر أستاذ موزع غير قابل للتغيير باستخدام آلية إثبات العمل (Proof of Work)، التجزئة بـ SHA-256، مزامنة الأقران (P2P)، توافق أطول سلسلة صالحة (Longest-Valid-Chain Consensus)، وقاعدة بيانات SQLite.

## architecture diagram

```
                    ┌──────────────────────┐
                    │   Bank Mirror CLI    │
                    │  (سطر أوامر البنك)   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Bank Mirror Server  │
                    │  (خادم البنك - 8000) │
                    └──────────┬───────────┘
                               │ إيداع/سحب/تحويل
                               ▼
    ┌─────────────────────────────────────────────┐
    │          شبكة البلوكتشين (P2P)              │
    │                                              │
    │  ┌──────────┐   ┌──────────┐   ┌──────────┐ │
    │  │ Node 5000│◄──►│ Node 5001│◄──►│ Node 5002│ │
    │  └──────────┘   └──────────┘   └──────────┘ │
    │       │              │              │        │
    │  ┌──────────┐   ┌──────────┐   ┌──────────┐ │
    │  │ SQLite   │   │ SQLite   │   │ SQLite   │ │
    │  └──────────┘   └──────────┘   └──────────┘ │
    └─────────────────────────────────────────────┘
```

## المتطلبات

- Python 3.10+
- Flask
- requests
- pytest

## التثبيت

```bash
# 1. تثبيت الحزم
pip install -r requirements.txt

# 2. تشغيل 3 عقد بلوكتشين (في 3 نوافذ مختلفة)
python -m blockchain.node 5000
python -m blockchain.node 5001
python -m blockchain.node 5002

# 3. تسجيل العقد في الشبكة (في نافذة رابعة)
python -m blockchain.node 5000 register

# 4. تشغيل خادم بنك المرآة
python -m bank_mirror.server 8000

# 5. استخدام عميل البنك
python -m bank_mirror.client
```

## هيكل المشروع

```
├── blockchain/          # نواة البلوكتشين
│   ├── block.py         # نموذج الكتلة (Block)
│   ├── blockchain.py    # سلسلة الكتل (Blockchain)
│   ├── config.py        # الإعدادات
│   ├── consensus.py     # آلية التوافق (Consensus)
│   ├── node.py          # عقدة P2P
│   ├── storage.py       # تخزين SQLite
│   ├── utils.py         # دوال مساعدة
│   └── validation.py    # التحقق من الصحة
├── api/                 # REST API
│   ├── app.py           # مصنع تطبيق Flask
│   ├── routes.py        # نقاط النهاية
│   ├── schemas.py       # التحقق من صحة الطلبات
│   └── errors.py        # معالجة الأخطاء
├── bank_mirror/         # نظام بنك المرآة
│   ├── server.py        # خادم البنك
│   ├── client.py        # عميل سطر الأوامر
│   ├── service.py       # منطق الأعمال
│   └── models.py        # نماذج البيانات
├── tests/               # الاختبارات (89 اختبارًا)
├── data/                # قواعد بيانات SQLite
├── requirements.txt
├── run_demo.py          # سكريبت التشغيل التجريبي
└── README.md
```

## نقاط نهاية API

### البلوكتشين (المنفذ 5000-5002)

| المسار | الطريقة | الوصف |
|--------|---------|-------|
| `/` | GET | قائمة نقاط النهاية |
| `/health` | GET | فحص صحة العقدة |
| `/chain` | GET | عرض سلسلة الكتل كاملة |
| `/pending` | GET | عرض المعاملات المعلقة |
| `/mine` | GET | تعدين كتلة جديدة |
| `/transactions/new` | POST | إضافة معاملة جديدة |
| `/nodes/register` | POST | تسجيل عقدة جديدة |
| `/nodes/resolve` | GET | تشغيل التوافق |
| `/nodes` | GET | قائمة العقد المسجلة |
| `/validation/chain` | GET | التحقق من صحة السلسلة |
| `/blocks/receive` | POST | استقبال كتلة من عقدة أخرى |

### بنك المرآة (المنفذ 8000)

| المسار | الطريقة | الوصف |
|--------|---------|-------|
| `/health` | GET | فحص صحة الخادم |
| `/send/deposit` | POST | إيداع |
| `/send/withdrawal` | POST | سحب |
| `/send/transfer` | POST | تحويل |
| `/send/custom` | POST | معاملة مخصصة |
| `/status` | GET | حالة الحسابات |
| `/history` | GET | سجل المعاملات |

## الأوامر السريعة

```bash
# التعدين
curl -X GET http://127.0.0.1:5000/mine

# إيداع
python -m bank_mirror.client deposit ACC001 5000

# سحب
python -m bank_mirror.client withdrawal ACC001 1000

# تحويل
python -m bank_mirror.client transfer ACC001 ACC002 500

# حالة الحسابات
python -m bank_mirror.client status

# تشغيل الاختبارات
python -m pytest tests/ -v
```

## الميزات

- إثبات العمل (PoW) مع صعوبة قابلة للتعديل (افتراضي: 4 أصفار)
- تخزين SQLite مع استمرارية واستعادة موثوقة
- مزامنة آلية بين العقد كل 30 ثانية
- توافق أطول سلسلة صالحة
- معالجة أخطاء JSON مع رموز حالة HTTP
- 89 اختبارًا للتغطية الكاملة للوظائف
