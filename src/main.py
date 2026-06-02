import sys

from config import Config
from services.ai_service import AIService
from services.search_service import SearchService


def _format_monster(row: dict, source: str | None = None) -> str:
    attrs = " / ".join(filter(None, [row.get("attribute_1"), row.get("attribute_2")]))
    types = " / ".join(filter(None, [row.get("type_1"), row.get("type_2"), row.get("type_3")]))
    leader = row.get("leader_skill_name_en") or "—"
    active = row.get("active_skill_name_en") or "—"
    tag = source or row.get("_source", "?")
    return (
        f"  [{tag}] #{row['monster_id']} | {row['name_en']}"
        f" | R{row.get('rarity', '?')}"
        f" | {attrs or '?'}"
        f" | {types or '?'}"
        f"\n    Leader: {leader}"
        f"\n    Active: {active}"
    )


def _print_search_results(result: dict) -> None:
    merged = result.get("merged") or []
    if not merged:
        print("❌ Không tìm thấy kết quả.")
        if result.get("filters"):
            print(f"   Bộ lọc: {result['filters']}")
        return

    structured_n = len(result.get("sqlite_structured") or [])
    vector_n = len(result.get("vector") or [])
    print(f"✅ {len(merged)} kết quả (SQL có cấu trúc: {structured_n}, Vector: {vector_n})")
    if result.get("filters"):
        print(f"   Bộ lọc: {result['filters']}")
    for row in merged:
        print(_format_monster(row))


def main() -> None:
    print("🤖 PAD AI Assistant — Hybrid Search (SQLite tag/stats + Gemini)")

    try:
        require_ai = "--ai" in sys.argv
        args = [a for a in sys.argv[1:] if a != "--ai"]

        if require_ai:
            Config.validate(require_gemini=True)

        print(f"✅ Chế độ: {Config.ENV}")
        print(f"📂 SQLite: {Config.SQLITE_DB_PATH}")
        print(f"📂 ChromaDB: {Config.CHROMA_DB_DIR}")

        service = SearchService()
        service._sqlite.connect()
        ai = AIService() if Config.GEMINI_API_KEY else None

        print("\n--- Structured Search ---")
        print("Ví dụ: 'Fire leader reduce damage và combo'")
        print("       'active void damage absorb và recover bind'")
        print("Gõ 'exit' để thoát.")
        if ai:
            print("Thêm flag --ai khi chạy để Gemini tổng hợp câu trả lời.")
        else:
            print("⚠️ Chưa có GEMINI_API_KEY — chỉ parse fallback / SQL.")

        while True:
            user_input = input("\nCâu hỏi: ")
            if user_input.strip().lower() == "exit":
                print("Tạm biệt rồng thần!")
                break

            query = user_input.strip()
            if not query:
                continue

            print(f"🔍 Đang xử lý '{query}'...")
            result = service.ask(
                query,
                use_ai_parser=bool(Config.GEMINI_API_KEY),
                use_vector_fallback=True,
            )
            _print_search_results(result)

            if require_ai and ai and result.get("merged"):
                print("\n--- Gemini ---")
                answer = ai.answer_from_search(
                    query,
                    result["merged"],
                    filters_json=result.get("filters"),
                )
                print(answer)

        service._sqlite.close()

    except FileNotFoundError as e:
        print(f"💥 Không tìm thấy database: {e}")
        print("   Đặt DadGuide SQLite vào data/pad_cards.db (hoặc SQLITE_DB_PATH trong .env).")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Lỗi: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
