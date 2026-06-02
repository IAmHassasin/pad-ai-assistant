# PAD AI Assistant

Trợ lý AI cho Puzzle & Dragons — **Hybrid Search có cấu trúc** trên schema DadGuide (SQLite tag/stats + tùy chọn ChromaDB + Gemini).

Thiết kế chi tiết: [docs/Thiet_Ke_AI_Database_PAD.md](docs/Thiet_Ke_AI_Database_PAD.md)

## Luồng xử lý

```
Câu hỏi → Gemini (JSON tag/stats) → SQLite lọc cứng → ChromaDB (tập nhỏ) → Gemini trả lời
```

1. **QueryParser** — Gemini ánh xạ câu hỏi → `SearchFilters` (leader/active tag_id, attribute, v.v.)
2. **SQLite** — `search_structured()` JOIN `leader_skills`, `active_skills`, `active_parts`
3. **ChromaDB** (tùy chọn) — vector trên ~50–100 pet đã lọc, không quét 14k
4. **AIService** — tổng hợp tiếng Việt từ top 3–10 kết quả

## Cấu trúc

```
pad-ai-assistant/
├── docs/Thiet_Ke_AI_Database_PAD.md
├── data/                    # pad_cards.db + chroma_db (gitignored)
├── scripts/
│   ├── generate_patterns.py
│   ├── index_chroma.py
│   └── test_structured_search.py
├── src/
│   ├── models/search_filters.py
│   ├── database/            # sqlite_client, tag_utils, vector_client
│   ├── services/            # query_parser, search_service, ai_service
│   └── main.py
└── requirements.txt
```

## Yêu cầu

**Python 3.11** (khớp Dockerfile). Python 3.14 thường không cài được `chromadb`.

## Cài đặt (Windows)

```powershell
cd D:\DevSamurai\pad-ai-assistant
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`.env`:

```env
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
SQLITE_DB_PATH=data/pad_cards.db
CHROMA_DB_DIR=data/chroma_db
```

**Database:** file DadGuide SQLite (`pad_cards.db`). Tag DadGuide + bảng bổ sung `leader_effect_types` / `active_effect_types` (chạy `python scripts/init_custom_effects.py` lần đầu).

### Custom effect types (bổ sung tag)

```powershell
python scripts/init_custom_effects.py
python scripts/manage_effects.py list
python scripts/manage_effects.py set-skill active 123 pierce_void_dmg --turns 2
python scripts/parse_skills_to_effects.py --side active --limit 100
```

### Sinh regex patterns từ skill DB (Gemini)

```powershell
python scripts/generate_patterns.py
```

Cần `GEMINI_API_KEY`. Kết quả: `data/pad_generated_patterns.json`.

### Test SQL có cấu trúc (không cần API)

```powershell
python scripts/test_structured_search.py
```

### Index ChromaDB (tùy chọn, fallback semantic)

```powershell
python scripts/index_chroma.py
```

### CLI

```powershell
python src/main.py
python src/main.py --ai
```

- Không `--ai`: in danh sách pet + bộ lọc JSON
- `--ai`: thêm câu trả lời Gemini (cần `GEMINI_API_KEY`)

## Biến môi trường

| Biến | Mô tả |
|------|--------|
| `GEMINI_API_KEY` | Google AI Studio — parse câu hỏi + trả lời (`--ai`) |
| `GEMINI_MODEL` | Model API (mặc định `gemini-2.5-flash`) |
| `SQLITE_DB_PATH` | Đường dẫn SQLite |
| `CHROMA_DB_DIR` | Thư mục ChromaDB |

## Ví dụ câu hỏi

- `Fire pet active recover bind`
- `leader reduce damage and extra combos`
- `active bypass void damage and attribute absorb`

## Docker

```bash
docker build -t pad-ai-assistant .
docker run --env-file .env pad-ai-assistant
```

## Lỗi thường gặp

| Lỗi | Xử lý |
|------|--------|
| Không tìm thấy database | Đặt `pad_cards.db` vào `data/` hoặc sửa `.env` |
| Không có kết quả structured | Chạy `test_structured_search.py`; kiểm tra tag trong DB |
| Chroma trống | `python scripts/index_chroma.py` |
| `No module named '_cffi_backend'` | Trong venv: `pip install --force-reinstall cffi` rồi chạy lại |
| `404 models/gemini-2.0-flash` | Sửa `.env`: `GEMINI_MODEL=gemini-2.5-flash` hoặc `gemini-flash-latest` |
