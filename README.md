# Trendyol Review Bot

Trendyol ürün yorumlarına **RAG (Retrieval-Augmented Generation)** tabanlı otomatik yanıt üreten yapay zeka chatbot'u.

Bir Trendyol ürün URL'si verildiğinde, ürünün bilgilerini ve müşteri yorumlarını çeker, vektör veritabanına kaydeder ve gelen yeni yorumlara bağlam odaklı, profesyonel Türkçe yanıtlar üretir.

##  Mimari

```
POST /scrape (Trendyol URL)
       ↓
  Selenium Scraper → window.__INITIAL_STATE__ JSON extraction
       ↓
  sentence-transformers (Türkçe embedding)
       ↓
  ChromaDB (vektör veritabanı)

POST /chat (product_id + yorum)
       ↓
  ChromaDB semantic search (benzer yorumları bul)
       ↓
  Claude Haiku 4.5 + system prompt + bağlam
       ↓
  Profesyonel Türkçe yanıt
```

##  Tech Stack

| Katman | Teknoloji |
|--------|-----------|
| Backend | FastAPI + Pydantic v2 |
| LLM | Anthropic Claude Haiku 4.5 |
| Embedding | sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) |
| Vector DB | ChromaDB |
| Scraping | Selenium + selenium-stealth |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |

##  Kurulum ve Çalıştırma

### Ön Koşullar
- Docker ve Docker Compose
- Anthropic API anahtarı → [console.anthropic.com](https://console.anthropic.com)

### 1. Repo'yu klonla
```bash
git clone https://github.com/your-username/trendyol-review-bot.git
cd trendyol-review-bot
```

### 2. `.env` dosyasını oluştur
```bash
cp .env.example .env
```
`.env` dosyasındaki `ANTHROPIC_API_KEY` değerini kendi API anahtarınla değiştir.

### 3. Docker ile başlat
```bash
docker compose up -d --build
```

### 4. Swagger UI
Tarayıcında aç: **http://localhost:8000/docs**

## 📡 API Kullanımı

### 1. Ürün Scrape Et
```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.trendyol.com/.../p-12345"}'
```
```json
{"product_id": "12345", "product_name": "Ürün Adı", "review_count": 15, "message": "15 belge ChromaDB'ye kaydedildi."}
```

### 2. Yorum Yanıtla (RAG + Claude)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"product_id": "12345", "review_text": "Ürün güzel ama kargo geç geldi"}'
```
```json
{"product_id": "12345", "generated_reply": "Değerli müşterimiz, ürünümüzü beğenmenize sevindik...", "context_used": 3}
```

### 3. Kayıtlı Ürünleri Listele
```bash
curl http://localhost:8000/products
```

##  Proje Yapısı

```
trendyol-review-bot/
├── app/
│   ├── main.py                # FastAPI app + lifespan
│   ├── config.py              # Pydantic Settings (.env)
│   ├── models/                # Request/Response modelleri
│   ├── routers/               # /scrape, /chat, /products
│   ├── services/
│   │   ├── scraper.py         # Selenium + __INITIAL_STATE__
│   │   ├── embedder.py        # ChromaDB + sentence-transformers
│   │   └── claude_client.py   # Anthropic Claude wrapper
│   └── prompts/
│       └── system_prompt.txt  # Türkçe mağaza asistanı prompt'u
├── tests/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

##  Ortam Değişkenleri

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `ANTHROPIC_API_KEY` | Anthropic API anahtarı | *(zorunlu)* |
| `MODEL_NAME` | Claude model adı | `claude-haiku-4-5-20251001` |
| `CHROMA_PATH` | ChromaDB veritabanı yolu | `./chroma_db` |
| `SCRAPER_HEADLESS` | Headless Chrome | `true` |
| `MAX_REVIEWS_PER_PRODUCT` | Max yorum sayısı | `50` |

