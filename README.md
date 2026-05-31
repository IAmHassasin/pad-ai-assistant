# PAD AI Assistant

Trợ lý AI cho Puzzle & Dragons — kiến trúc Clean / Modular bằng Python, tách lớp dữ liệu (SQLite, ChromaDB, Scraper) và nghiệp vụ AI (Gemini).

## Cách hoạt động

Người dùng đặt câu hỏi qua CLI (`main.py`). Hệ thống xử lý theo luồng sau:

1. **Cấu hình** — `config.py` đọc biến môi trường (API key, đường dẫn DB) và kiểm tra trước khi chạy.
2. **Hybrid Search** — `SearchService` tra cứu song song hai nguồn:
   - **SQLite** (`sqlite_client`): tìm monster/card theo tên hoặc metadata có cấu trúc (~14.000 bản ghi).
   - **ChromaDB** (`vector_client`): tìm ngữ nghĩa qua embedding (guide, mô tả, nội dung dài).
3. **Trả lời AI** — `AIService` gửi câu hỏi kèm ngữ cảnh từ bước 2 lên **Gemini 1.5 Flash**, sinh câu trả lời dựa trên dữ liệu PAD thay vì suy đoán.
4. **Scrapers** (mở rộng sau) — `game8_scraper` và `youtube_scraper` thu thập team guide / video metadata để bổ sung vào vector store.

```
Câu hỏi → main.py → SearchService → SQLite + ChromaDB
                              ↓
                         AIService (Gemini) → Câu trả lời
```

Hiện tại CLI đang ở chế độ demo; bước nối `SearchService` + `AIService` vào `main.py` sẽ hoàn thiện luồng trên.

## Cấu trúc

```
pad-ai-assistant/
├── .github/workflows/deploy.yml
├── data/                    # SQLite + ChromaDB (gitignored)
├── src/
│   ├── config.py
│   ├── database/            # Infrastructure
│   ├── scrapers/
│   ├── services/            # Domain / AI
│   └── main.py
├── Dockerfile
└── requirements.txt
```

## Cài đặt local

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate   # Linux / macOS

pip install -r requirements.txt
cp .env.example .env            # Điền GEMINI_API_KEY
python src/main.py
```

## Biến môi trường

| Biến | Mô tả |
|------|--------|
| `ENV` | `development` hoặc `production` |
| `GEMINI_API_KEY` | API key từ [Google AI Studio](https://aistudio.google.com/) |
| `SQLITE_DB_PATH` | Đường dẫn file SQLite (mặc định `data/pad_cards.db`) |
| `CHROMA_DB_DIR` | Thư mục ChromaDB (mặc định `data/chroma_db`) |

## Docker (OCI / ARM64)

```bash
docker build -t pad-ai-assistant .
docker run --env-file .env pad-ai-assistant
```

## Bước tiếp theo

1. Nạp dữ liệu ~14.000 monster vào `data/pad_cards.db`
2. Triển khai embedding / hybrid search qua `sqlite_client` và `vector_client`
3. Kết nối `search_service` + `ai_service` trong `main.py`
