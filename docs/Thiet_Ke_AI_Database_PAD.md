# Thiết kế PAD AI Assistant — Hybrid Search có cấu trúc

## Tổng quan

Với ~14.000 monster, **không** ném toàn bộ JSON vào Gemini mỗi lượt. Luồng tối ưu:

```
[Câu hỏi User]
       │
       ▼
┌──────────────────────────────────────────────┐
│ 1. Gemini → JSON điều kiện (tag_id, stats)   │
└──────────────────┬───────────────────────────┘
                   │ (~14k → vài chục–trăm)
                   ▼
┌──────────────────────────────────────────────┐
│ 2. SQLite DadGuide (tag + chỉ số số)         │
│    leader_skill_tags, active_skill_tags,       │
│    active_parts (chi tiết từng effect)       │
└──────────────────┬───────────────────────────┘
                   │ (top 3–10)
                   ▼
┌──────────────────────────────────────────────┐
│ 3. ChromaDB (tùy chọn, trên tập đã lọc)      │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│ 4. Gemini Flash — tổng hợp câu trả lời        │
└──────────────────────────────────────────────┘
```

Chi phí ước tính: **~2 VNĐ / câu** (prompt ~1.000 token), so với ~57.000 VNĐ nếu gửi cả 14k thẻ.

## Hai lớp tag (DadGuide + Custom)

| Lớp | Bảng | Khi nào dùng |
|-----|------|----------------|
| DadGuide | `leader_skill_tags`, `active_skill_tags`, `active_parts.tags` | Data có sẵn, đủ coverage |
| **Custom** | `leader_effect_types`, `active_effect_types` + `*_skill_effects` | Bổ sung khi DadGuide thiếu/sai |

Custom gắn theo **`leader_skill_id` / `active_skill_id`** (một lần parse → mọi monster dùng skill đó).

```sql
-- Danh mục effect (bạn định nghĩa key_name)
CREATE TABLE leader_effect_types (
    effect_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_name TEXT UNIQUE, display_name TEXT, description TEXT
);
CREATE TABLE active_effect_types (...);

-- Gán effect cho skill (nhiều effect / skill)
CREATE TABLE leader_skill_effects (
    leader_skill_id INTEGER, effect_type_id INTEGER,
    value_1 REAL, value_2 REAL, turn_duration INTEGER,
    source TEXT DEFAULT 'manual',  -- manual | gemini
    PRIMARY KEY (leader_skill_id, effect_type_id)
);
CREATE TABLE active_skill_effects (...);
```

Khởi tạo + seed key mặc định:

```powershell
python scripts/init_custom_effects.py
python scripts/manage_effects.py list
python scripts/manage_effects.py set-skill active 949 pierce_void_dmg --turns 2
python scripts/parse_skills_to_effects.py --side active --limit 50
```

## Schema DadGuide (đã có sẵn)

DadGuide đã chuẩn hóa một phần:

| Lớp | Bảng | Mục đích |
|-----|------|----------|
| Leader | `leader_skills` + `tags` `(26),(37)` | Tag + `max_atk`, `max_combos`, `bonus_damage` |
| Active (thô) | `active_skills` + `tags` | Tag cấp skill (vd. Void Damage = 12) |
| Active (chi tiết) | `active_parts` → `active_subskills_parts` | Từng dòng effect (vd. 240/250 = pierce absorb) |

### Leader skill (~4–5 kiểu giá trị)

- `max_hp`, `max_atk`, `max_rcv` — hệ số nhân
- `max_combos` — thêm combo
- `bonus_damage` / `mult_bonus_damage` — true damage
- `tags` — Enhanced ATK, Reduce Damage, Extra Combos...

### Active skill (nhiều tổ hợp)

- **Cấp skill**: `active_skills.tags` — AND nhiều tag
- **Cấp part**: join qua `active_skills_subskills` → `active_subskills_parts` → `active_parts.tags` — chính xác hơn (void dmg vs void attr absorb)

Ví dụ tag quan trọng:

| ID | Tên |
|----|-----|
| 12 | Void Damage |
| 240 | Void damage absorbs |
| 250 | Void Att. Absorbs |
| 41 | Recover Bind |
| 32 | Reduce Damage (leader) |
| 211 | Extra Combos (leader) |

## Codebase

```
src/
├── models/search_filters.py    # Pydantic: MonsterFilters, LeaderFilters, ActiveFilters
├── database/
│   ├── sqlite_client.py        # search_structured(), list_*_tags()
│   └── tag_utils.py
├── services/
│   ├── query_parser.py         # Gemini → SearchFilters
│   ├── search_service.py       # ask(), structured_search()
│   └── ai_service.py           # answer_from_search()
└── main.py
```

## Ví dụ SQL (tương đương code)

Fire + active part pierce absorb:

```sql
SELECT DISTINCT m.monster_id
FROM monsters m
WHERE m.attribute_1_id = 1  -- Fire
  AND EXISTS (
    SELECT 1 FROM active_skills ac_p
    JOIN active_skills_subskills ass ON ac_p.active_skill_id = ass.active_skill_id
    JOIN active_subskills_parts asp ON ass.active_subskill_id = asp.active_subskill_id
    JOIN active_parts ap ON asp.active_part_id = ap.active_part_id
    WHERE ac_p.active_skill_id = m.active_skill_id
      AND ap.tags LIKE '%(240)%'
      AND ap.tags LIKE '%(250)%'
  );
```

## Khi nào cần Vector / ingest mới?

- Câu hỏi mơ hồ, không map được tag
- Skill mới chưa có tag trong DadGuide
- Team guide / YouTube (mở rộng sau → `template_teams`, scrapers)

ChromaDB vẫn hữu ích như **bước 2 trên tập đã lọc**, không thay SQL.

## Hạ tầng OCI Free Tier

- SQLite + Chroma local: &lt; 300MB, RAM dư trên ARM 24GB
- Deploy: Docker + `docker-compose` volume `./data`
- Chưa cần folder `iac/` cho 1 VPS — GitHub Actions + compose đủ

## Mở rộng (team build, Game8/YouTube)

```sql
CREATE TABLE template_teams (
    id INTEGER PRIMARY KEY,
    leader_id INTEGER,
    sub1_id INTEGER, sub2_id INTEGER, sub3_id INTEGER, sub4_id INTEGER,
    helper_id INTEGER,
    source_url TEXT,
    description TEXT
);
```

Tra team mẫu = **SQL thuần, 0 token**. Gemini chỉ format câu trả lời.

## Parse skill mới (một lần)

Nếu thiếu tag: script batch Gemini/Regex → bổ sung tag (xem hội thoại thiết kế `parse_active_skill_to_tags`). Ưu tiên dùng dữ liệu DadGuide đã parse sẵn.
