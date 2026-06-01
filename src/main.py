import sys

from config import Config
from services.search_service import SearchService


def _format_monster(row: dict, source: str | None = None) -> str:
    attrs = " / ".join(filter(None, [row.get("attribute_1"), row.get("attribute_2")]))
    types = " / ".join(filter(None, [row.get("type_1"), row.get("type_2"), row.get("type_3")]))
    leader = row.get("leader_skill_name_en") or "—"
    tag = source or row.get("_source", "?")
    return (
        f"  [{tag}] #{row['monster_id']} | {row['name_en']}"
        f" | R{row.get('rarity', '?')}"
        f" | {attrs or '?'}"
        f" | {types or '?'}"
        f"\n    Leader: {leader}"
    )


def _print_hybrid_results(query: str, result: dict) -> None:
    merged = result.get("merged") or []
    if not merged:
        print(f"❌ Không tìm thấy kết quả cho '{query}'.")
        print("   Chạy `py scripts/index_chroma.py` nếu chưa embed ChromaDB.")
        return

    sqlite_n = len(result.get("sqlite") or [])
    vector_n = len(result.get("vector") or [])
    print(f"✅ {len(merged)} kết quả (SQLite: {sqlite_n}, ChromaDB: {vector_n}):")
    for row in merged:
        print(_format_monster(row))


def main():
    print("🤖 Khởi tạo Hệ thống Trợ lý Bách Khoa Toàn Thư Puzzle & Dragons...")

    try:
        Config.validate()
        print(f"✅ Cấu hình hợp lệ. Chế độ: {Config.ENV}")
        print(f"📂 SQLite: {Config.SQLITE_DB_PATH}")
        print(f"📂 ChromaDB: {Config.CHROMA_DB_DIR}")

        service = SearchService()
        service._sqlite.connect()
        print("✅ Đã kết nối SQLite + ChromaDB.")

        print("\n--- Hybrid Search (SQLite tên + ChromaDB ngữ nghĩa) ---")
        print("Ví dụ: 'Ra' | 'leader skill giảm cooldown fire team'")
        print("Gõ 'exit' để thoát.")

        while True:
            user_input = input("\nCâu hỏi: ")
            if user_input.strip().lower() == "exit":
                print("Tạm biệt rồng thần!")
                break

            query = user_input.strip()
            if not query:
                continue

            print(f"🔍 Đang tìm '{query}'...")
            result = service.hybrid_search(query)
            _print_hybrid_results(query, result)

        service._sqlite.close()

    except FileNotFoundError as e:
        print(f"💥 Không tìm thấy database: {e}")
        print("   Hãy đặt file DadGuide SQLite vào data/pad_cards.db (hoặc cấu hình SQLITE_DB_PATH).")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Lỗi hệ thống khi khởi động: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
