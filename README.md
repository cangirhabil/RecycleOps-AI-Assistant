# RecycleOps AI Assistant

Slack üzerindeki hata kayıtlarını ve çözüm konuşmalarını otomatik olarak okuyan, öğrenen ve gelecekte benzer sorunlar yaşandığında teknik ekibe anında çözüm sunan yapay zeka destekli bir asistan.

## 🎯 Amaç

Sistemin temel amacı **"Kurumsal Hafıza"** oluşturmak ve teknik desteği hızlandırmaktır.

## ⚙️ Sistem Nasıl Çalışır?

Sistem sürekli bir döngü halinde 3 aşamada çalışır:

1. **Dinleme ve Takip**: Slack kanallarına düşen tüm makine arıza bildirimlerini ve altına yazılan yorumları takip eder.
2. **Akıllı Analiz ve Öğrenme**: Bir arıza ile ilgili konuşma bittiğinde (son mesajdan 12 saat sonra), yapay zeka tüm konuşmayı okur ve çözümü hafızasına kaydeder.
3. **Destek ve Çözüm**: Yeni bir arıza meydana geldiğinde, asistan hafızasındaki geçmiş tecrübelere bakar ve çözüm önerir.

## ✨ Temel Özellikler

| Özellik | Komut | Açıklama |
|---------|-------|----------|
| Otomatik Öğrenme | - | 12 saat kuralı ile konuşmaları otomatik analiz eder |
| Akıllı Arama | `/search [sorun]` | Geçmiş çözümlerde arama yapar |
| Konu İçi Öneri | `/cozum-getir` | Thread içindeki soruna çözüm önerir |
| Hızlı Kayıt | `/cozum-ekle` | Konuşmayı anında hafızaya ekler |
| Proaktif Destek | - | Yeni hatalara otomatik çözüm önerir |
| Uzman Yönlendirme | - | Çözüm bulunamazsa uzman önerir |

## 🏗️ Teknoloji Stack

- **Backend**: Python 3.11+
- **Slack**: Slack Bolt SDK
- **Vector DB**: ChromaDB (local)
- **SQL DB**: PostgreSQL
- **RAG**: LangChain + OpenAI
- **Scheduling**: APScheduler

## 📦 Kurulum

### Gereksinimler

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (opsiyonel)

### 1. Repository'yi Klonla

```bash
git clone https://github.com/cangirhabil/RecycleOps-AI-Assistant.git
cd RecycleOps-AI-Assistant
```

### 2. Virtual Environment Oluştur

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Bağımlılıkları Yükle

```bash
pip install -e ".[dev]"
```

### 4. Environment Variables

```bash
cp .env.example .env
# .env dosyasını düzenle ve gerekli değerleri gir
```

### 5. Veritabanını Başlat

```bash
# Docker ile
docker-compose up -d postgres

# Migration'ları çalıştır
alembic upgrade head
```

### 6. Uygulamayı Başlat

```bash
python -m src.main
```

## 🔧 Slack App Kurulumu

1. [Slack API](https://api.slack.com/apps) üzerinden yeni bir app oluşturun
2. **Socket Mode** etkinleştirin
3. **Event Subscriptions** altında şu event'leri ekleyin:
   - `message.channels`
   - `message.groups`
   - `app_mention`
4. **Slash Commands** ekleyin:
   - `/search`
   - `/cozum-getir`
   - `/cozum-ekle`
5. **OAuth Scopes** (Bot Token Scopes):
   - `channels:history`
   - `channels:read`
   - `chat:write`
   - `commands`
   - `groups:history`
   - `groups:read`
   - `users:read`

## 📁 Proje Yapısı

```
RecycleOps-AI-Assistant/
├── src/
│   ├── main.py              # Uygulama giriş noktası
│   ├── config.py            # Konfigürasyon yönetimi
│   ├── slack/               # Slack bot modülleri
│   ├── rag/                 # RAG pipeline modülleri
│   ├── learning/            # Otomatik öğrenme modülleri
│   ├── database/            # Veritabanı modülleri
│   ├── services/            # İş mantığı servisleri
│   └── utils/               # Yardımcı fonksiyonlar
├── tests/                   # Test dosyaları
├── migrations/              # Alembic migration'ları
└── data/chroma/             # ChromaDB verileri
```

## 🧪 Test

```bash
pytest tests/ -v --cov=src
```

## 📝 Lisans

MIT License
