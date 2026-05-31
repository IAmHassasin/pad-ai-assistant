import sys
from config import Config


def main():
    print("🤖 Khởi tạo Hệ thống Trợ lý Bách Khoa Toàn Thư Puzzle & Dragons...")

    try:
        # 1. Kiểm tra cấu hình hệ thống
        Config.validate()
        print(f"✅ Cấu hình hợp lệ. Chế độ: {Config.ENV}")
        print(f"📂 Cơ sở dữ liệu đích: {Config.SQLITE_DB_PATH}")

        # 2. Luồng demo nhận câu hỏi (Giao diện CLI để test local)
        print("\n--- Hệ thống đã sẵn sàng hỏi đáp ---")
        while True:
            user_input = input("\nBạn muốn hỏi gì về PAD? (Gõ 'exit' để thoát): ")
            if user_input.strip().lower() == "exit":
                print("Tạm biệt rồng thần!")
                break

            if user_input.strip():
                print(f"🔍 Đang xử lý câu hỏi: '{user_input}'...")
                # Các lớp search_service và ai_service sẽ được gọi tại đây ở các bước sau.
                print(
                    "⚠️ Lưu ý: Hãy nạp dữ liệu vào file data/pad_cards.db "
                    "để thực hiện Hybrid Search."
                )

    except Exception as e:
        print(f"💥 Lỗi hệ thống khi khởi động: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
