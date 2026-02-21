# 📄 Product Requirements Document (PRD)
## Career Assistant AI Agent
**Repo:** `agentic-cv-helper` | **Version:** 1.0.0 | **Status:** Draft

---

## 📋 Metadata

| Alan | Değer |
|------|-------|
| Proje Adı | Career Assistant AI Agent |
| Repo | github.com/\<username\>/agentic-cv-helper |
| Versiyon | 1.0.0 |
| Tech Stack | Python 3.11+, FastAPI, OpenAI API, LangChain, Telegram Bot API |
| Durum | Draft |

---

## 1. Executive Summary

`agentic-cv-helper`, potansiyel işverenlerden gelen mesajları otomatik olarak değerlendiren, profesyonel yanıtlar üreten ve bu yanıtları kullanıcıya göndermeden önce bir Evaluator Agent aracılığıyla kalite kontrolünden geçiren çok ajanlı (multi-agent) bir yapay zeka sistemidir.

Sistem dört temel bileşenden oluşur: **Career Agent** (birincil ajan), **Response Evaluator Agent** (yargıç ajan), **Notification Tool** ve **Unknown Question Detection Tool**. FastAPI ile sunulan REST API üzerinden mesajlar alınır, ajan döngüsü çalışır ve onaylanan yanıt kullanıcıya mobil bildirim eşliğinde iletilir.

---

## 2. Proje Hedefleri

### 2.1 Birincil Hedefler

- İşveren mesajlarını otomatik sınıflandırmak ve uygun profesyonel yanıtlar üretmek
- Üretilen yanıtları göndermeden önce kalite ve güvenlik açısından değerlendirmek
- Bilinmeyen veya riskli sorular için insan müdahalesini tetiklemek
- Kullanıcıyı her kritik adımda mobil bildirimle bilgilendirmek

### 2.2 Başarı Kriterleri

- Evaluator skoru ≥ 0.75 olan yanıtlar otomatik olarak gönderilmeli
- Bilinmeyen sorularda %100 insan bildirim oranı sağlanmalı
- Yanıt üretim süresi 15 saniyenin altında kalmalı
- 3 test senaryosunun tamamı başarıyla geçilmeli

---

## 3. Sistem Mimarisi

### 3.1 Agent Loop

```
İşveren Mesajı (POST /api/v1/message)
        │
        ▼
┌───────────────────────┐
│ Unknown Question Tool │  ◄── confidence < 0.4 → Telegram Bildirimi + Human Intervention
└───────────────────────┘
        │ (temiz)
        ▼
┌───────────────────────┐
│     Career Agent      │  ◄── CV/Profil bağlamı + GPT-4o
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  Evaluator Agent      │  ◄── LLM-as-Judge (5 kriter, 0-1 arası puan)
└───────────────────────┘
        │
   skor ≥ 0.75?
   ┌────┴────┐
  EVET      HAYIR
   │         │
   │    revizyon (maks. 3 iterasyon)
   │         │
   │    hâlâ başarısız → Telegram Bildirimi
   │
   ▼
Yanıt Onaylandı → Loglama → Telegram Bildirimi
```

### 3.2 Bileşen Tablosu

| Bileşen | Teknoloji | Sorumluluk |
|---------|-----------|------------|
| Career Agent | OpenAI GPT-4o + LangChain | CV bağlamında profesyonel yanıt üretimi |
| Evaluator Agent | OpenAI GPT-4o (LLM-as-Judge) | 5 kriterde yanıt değerlendirme ve puanlama |
| Unknown Q. Tool | Confidence Scoring + Keyword Match | Bilinmeyen sorular için insan devreye alımı |
| Notification Tool | Telegram Bot API | Mobil bildirim gönderimi |
| API Layer | FastAPI + Pydantic | REST endpoint, request/response validasyon |
| CV Context | Static JSON / RAG (FAISS) | Profil bilgisi bağlamı |
| Logging | Python logging + JSON | Skor ve olay kayıtları |

---

## 4. Proje Klasör Yapısı

```
agentic-cv-helper/
├── .venv/                          # Python sanal ortamı (git'e eklenmez)
├── .gitignore                      # Git ignore kuralları
├── .env.example                    # Örnek environment değişkenleri
├── README.md                       # Proje açıklaması ve kurulum
├── requirements.txt                # Python bağımlılıkları
├── pyproject.toml                  # Proje metadata (opsiyonel)
│
├── app/                            # Ana uygulama paketi
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # Ayarlar ve environment değişkenleri
│   │
│   ├── agents/                     # Agent tanımları
│   │   ├── __init__.py
│   │   ├── career_agent.py         # Birincil Career Agent
│   │   ├── evaluator_agent.py      # Response Evaluator (Judge) Agent
│   │   └── agent_loop.py           # Ajan döngüsü orkestrasyonu
│   │
│   ├── tools/                      # Agent araçları
│   │   ├── __init__.py
│   │   ├── notification_tool.py    # Telegram bildirim aracı
│   │   └── unknown_question_tool.py# Bilinmeyen soru tespiti
│   │
│   ├── models/                     # Pydantic modelleri
│   │   ├── __init__.py
│   │   ├── request_models.py       # API request şemaları
│   │   └── response_models.py      # API response şemaları
│   │
│   ├── prompts/                    # Prompt şablonları
│   │   ├── career_agent_prompt.py
│   │   └── evaluator_prompt.py
│   │
│   └── routers/                    # FastAPI router'ları
│       ├── __init__.py
│       └── message_router.py       # /api/v1/message endpoint
│
├── data/                           # Statik veri dosyaları
│   ├── cv_profile.json             # CV ve profil bilgisi — GİT'E EKLENMEMELİ
│   └── cv_profile_sample.json      # Örnek profil (paylaşılabilir)
│
├── logs/                           # Log dosyaları (git'e eklenmez)
│   └── .gitkeep
│
├── tests/                          # Test dosyaları
│   ├── __init__.py
│   ├── test_career_agent.py        # Test 1: Mülakat daveti
│   ├── test_evaluator.py           # Test 2: Teknik soru
│   ├── test_unknown_question.py    # Test 3: Bilinmeyen soru
│   └── conftest.py                 # Pytest fixtures
│
├── docs/                           # Dokümantasyon
│   ├── architecture_diagram.png    # Mimari akış şeması
│   ├── PRD.md                      # Bu döküman
│   ├── flow_diagram.md             # Mermaid akış diyagramı
│   └── report.md                   # 3-5 sayfalık rapor
│
└── scripts/                        # Yardımcı scriptler
    ├── setup_env.sh                # .venv kurulum scripti
    └── run_demo.py                 # Demo çalıştırma scripti
```

---

## 5. Bileşen Detayları

### 5.1 Career Agent (`app/agents/career_agent.py`)

CV profil bağlamını kullanarak işveren mesajına profesyonel yanıt üretir.

**Minimum Yetenekler:**
- Mülakat davetine kabul veya nazik ret yanıtı verme
- Teknik sorulara CV bağlamında yanıt verme
- İş tekliflerini nazikçe reddetme
- Belirsiz mesajlarda netleştirici sorular sorma

**Prompt Tasarımı:**
- `system`: Rol tanımı + CV özeti + ton talimatları (`professional`, `concise`, `polite`)
- `user`: İşveren mesajı
- Çıktı formatı: `{ "response": str, "confidence": float, "category": str }`

**Kategoriler:** `interview_invitation` | `technical_question` | `offer_decline` | `clarification` | `unknown`

---

### 5.2 Response Evaluator Agent (`app/agents/evaluator_agent.py`)

LLM-as-a-Judge yaklaşımıyla üretilen yanıtı göndermeden önce değerlendirir.

**Değerlendirme Kriterleri:**

| Kriter | Açıklama | Ağırlık |
|--------|----------|---------|
| Professional Tone | Dil resmi, saygılı ve açık mı? | %25 |
| Clarity | Mesaj net ve anlaşılır mı? | %20 |
| Completeness | Tüm sorular yanıtlandı mı? | %20 |
| Safety | Hallüsinasyon veya yanlış iddia var mı? | %25 |
| Relevance | Yanıt işveren mesajıyla ilgili mi? | %10 |

**Parametreler:**
- Eşik değeri: `0.75`
- Maksimum revizyon iterasyonu: `3`
- Başarısız olursa: insan bildirimi tetiklenir

**Davranış:**
```
skor ≥ 0.75  →  yanıt onaylanır, loglanır
skor < 0.75  →  revizyon talebi + feedback döner
3. iterasyon sonrası hâlâ < 0.75  →  Telegram bildirimi + human_intervention_required: true
```

---

### 5.3 Unknown Question Detection Tool (`app/tools/unknown_question_tool.py`)

Ajanın yanıtlayamayacağı veya yanıtlaması riskli olan durumları otomatik tespit eder.

**Tespit Kriterleri:**
- Career Agent `confidence` skoru `< 0.4`
- Maaş müzakeresi (belirli bir eşiğin ötesinde)
- Hukuki sorular ve sözleşme detayları
- CV'de yer almayan derin teknik alanlar
- Belirsiz veya çelişkili iş teklifleri

**Tetiklendiğinde:**
- Telegram üzerinden kullanıcıya bildirim gönderilir
- Olay `logs/` klasörüne JSON formatında kaydedilir
- API response'a `"human_intervention_required": true` eklenir

---

### 5.4 Notification Tool (`app/tools/notification_tool.py`)

Telegram Bot API kullanılarak aşağıdaki durumlarda mobil bildirim gönderilir:

- Yeni bir işveren mesajı geldiğinde
- Yanıt onaylanıp gönderildiğinde
- Bilinmeyen soru tespit edildiğinde
- Evaluator maksimum iterasyona ulaşıp başarısız olduğunda

---

## 6. API Endpoints

| Method | Endpoint | Açıklama | Response |
|--------|----------|----------|----------|
| `POST` | `/api/v1/message` | İşveren mesajı gönder | `response`, `score`, `status` |
| `GET` | `/api/v1/logs` | Son yanıt loglarını getir | log listesi |
| `GET` | `/api/v1/health` | Servis sağlık kontrolü | `status: ok` |
| `POST` | `/api/v1/test` | Test senaryosu çalıştır | `test_result`, `passed` |

**Örnek Request / Response:**

```json
// POST /api/v1/message
{
  "sender": "hr@company.com",
  "message": "We'd like to invite you for a technical interview next Tuesday."
}

// Response
{
  "response": "Thank you for the invitation...",
  "evaluator_score": 0.91,
  "category": "interview_invitation",
  "status": "approved",
  "human_intervention_required": false,
  "iterations": 1
}
```

---

## 7. Test Senaryoları

### Test 1 — Standart Mülakat Daveti
| Alan | Değer |
|------|-------|
| Dosya | `tests/test_career_agent.py` |
| Giriş | `"We'd like to invite you for a technical interview next Tuesday at 10 AM. Are you available?"` |
| Beklenen | Polite acceptance, date confirmation, professional tone |
| Min. Evaluator Skoru | `0.80` |
| Bildirim | ✅ Yeni mesaj + ✅ Yanıt onaylandı |

### Test 2 — Teknik Soru
| Alan | Değer |
|------|-------|
| Dosya | `tests/test_evaluator.py` |
| Giriş | `"Can you describe your experience with LangChain agents and tool-calling mechanisms?"` |
| Beklenen | CV'ye dayalı, doğru ve özlü teknik açıklama |
| Min. Evaluator Skoru | `0.75` |
| Bildirim | ✅ Yeni mesaj + ✅ Yanıt onaylandı |

### Test 3 — Bilinmeyen / Riskli Soru
| Alan | Değer |
|------|-------|
| Dosya | `tests/test_unknown_question.py` |
| Giriş | `"What is the minimum salary you would accept and are you willing to sign a non-compete clause?"` |
| Beklenen | `human_intervention_required: true`, Telegram bildirimi |
| Min. Evaluator Skoru | N/A (insan devreye girer) |
| Bildirim | ✅ Yeni mesaj + ✅ İnsan müdahalesi gerekiyor |

---

## 8. Environment & Setup

### 8.1 `.env.example`

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Agent Config
EVALUATOR_THRESHOLD=0.75
MAX_REVISION_ITERATIONS=3
UNKNOWN_CONFIDENCE_THRESHOLD=0.4

# App
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```

### 8.2 Kurulum Adımları

```bash
# 1. Repoyu klonla
git clone https://github.com/<username>/agentic-cv-helper.git
cd agentic-cv-helper

# 2. Sanal ortamı oluştur ve aktif et
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Environment dosyasını hazırla
cp .env.example .env
# .env dosyasını aç ve API key'leri doldur

# 5. Uygulamayı çalıştır
uvicorn app.main:app --reload

# 6. Testleri çalıştır
pytest tests/ -v
```

---

## 9. `.gitignore` İçeriği

```gitignore
# Virtual Environment
.venv/
venv/

# Environment Variables
.env

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/

# Logs
logs/*.log
logs/*.json

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Sensitive Data — CV profil bilgin bu dosyada, asla push etme!
data/cv_profile.json
```

---

## 10. Bonus Özellikler (Opsiyonel)

### 10.1 Konuşma Hafızası
- Her konuşma session ID ile takip edilir
- LangChain `ConversationBufferMemory` veya Redis ile geçmiş saklanır
- Çok turlu diyalog desteği sağlanır

### 10.2 Güven Skoru Görselleştirme
- FastAPI üzerinde `/dashboard` endpoint'i
- Her yanıtın evaluator skoru ve kriteri grafikle gösterilir
- Streamlit veya minimal HTML/JS frontend

### 10.3 Cloud Deployment
- Railway veya Render üzerinden otomatik deploy
- GitHub Actions ile CI/CD pipeline
- Environment secrets GitHub Secrets'tan yönetilir

---

## 11. Geliştirme Takvimi

| Gün | Aşama | Görevler |
|-----|-------|----------|
| 1-2 | Temel Kurulum | Repo, `.venv`, FastAPI skeleton, CV JSON, `.env.example` |
| 3-4 | Career Agent | Prompt tasarımı, OpenAI entegrasyonu, kategori sınıflandırma |
| 5-6 | Evaluator Agent | LLM-as-Judge prompt, revizyon döngüsü, loglama |
| 7 | Araçlar | Telegram notification tool, unknown question detection tool |
| 8 | Test Senaryoları | 3 test case yazımı ve pytest entegrasyonu |
| 9 | Dokümantasyon | Architecture diagram, flow diagram, rapor |
| 10 | Demo & Polish | Live demo hazırlığı, bonus özellikler (opsiyonel) |

---

*agentic-cv-helper | PRD v1.0*
