import os
import json
import sqlite3
import re
from typing import List, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from pydantic import BaseModel, Field

# Nạp cấu hình từ file .env
load_dotenv()

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/pad_cards.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 1. Định nghĩa cấu trúc Schema ép kiểu đầu ra JSON cho Gemini 2.5 Flash
class PatternMapping(BaseModel):
    skill_type: str = Field(description="Loại kỹ năng: 'active_skill' hoặc 'leader_skill'")
    tag_id: Optional[int] = Field(description="ID của tag cũ từ DB (nếu có), null nếu là tag mới phát hiện")
    tag_name_en: str = Field(description="Tên tiếng Anh của tag (tên cũ từ DB hoặc tên snake_case tự định nghĩa nếu là tag mới)")
    status: str = Field(description="Trạng thái phân tích: 'existing_tag' hoặc 'new_effect_detected'")
    regex_pattern: str = Field(description="Chuỗi Regex Python chính xác tuyệt đối để khớp với text desc_en thực tế trong game, sử dụng (\\d+) cho các biến số")
    example_matched_text: str = Field(description="Một đoạn text ví dụ thực tế được trích xuất từ mô tả kỹ năng mà regex này có thể khớp trúng")

class PatternMigrationSchema(BaseModel):
    patterns: List[PatternMapping]

# 2. Khởi tạo kết nối Gemini
if not GEMINI_API_KEY:
    raise ValueError("❌ Thiếu GEMINI_API_KEY trong cấu hình môi trường (.env)")
    
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')


def parse_tags_string(tags_str: str) -> list[int]:
    """
    Chuyển đổi chuỗi định dạng "(7),(19),(230)" thành mảng [7, 19, 230]
    """
    if not tags_str or tags_str.strip() == "":
        return []
    # Sử dụng tìm kiếm tất cả các cụm số nằm bên trong dấu ngoặc đơn
    ids = re.findall(r'\((\d+)\)', tags_str)
    return [int(tag_id) for tag_id in ids]

def fetch_db_metadata():
    """Đọc dữ liệu thô và cấu trúc danh mục tag hiện tại từ SQLite"""
    print(f"📂 Đang kết nối tới SQLite Database tại: {SQLITE_DB_PATH}")
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # 1. Lấy danh mục Active Skill Tags hiện có
    cursor.execute("SELECT active_skill_tag_id, name_en FROM active_skill_tags")
    as_tags = {row[0]: row[1] for row in cursor.fetchall()}
    
    # 2. Lấy danh mục Leader Skill Tags hiện có
    cursor.execute("SELECT leader_skill_tag_id, name_en FROM leader_skill_tags")
    ls_tags = {row[0]: row[1] for row in cursor.fetchall()}
    
    # 3. Lấy danh sách Active Skill độc bản (Lọc trùng chuỗi mô tả)
    cursor.execute("""
        SELECT DISTINCT desc_en, tags 
        FROM active_skills 
        WHERE desc_en IS NOT NULL AND desc_en != '' 
        LIMIT 250
    """)
    active_skills_sample = []
    for row in cursor.fetchall():
        active_skills_sample.append({
            "desc": row[0],
            "tags_id_list": parse_tags_string(row[1]) # Trả về dạng [7, 19, 230] để AI dễ đọc mapping
        })
    
    # 4. Lấy danh sách Leader Skill độc bản (Lọc trùng chuỗi mô tả)
    cursor.execute("""
        SELECT DISTINCT desc_en, tags 
        FROM leader_skills 
        WHERE desc_en IS NOT NULL AND desc_en != '' 
        LIMIT 250
    """)
    leader_skills_sample = []
    for row in cursor.fetchall():
        leader_skills_sample.append({
            "desc": row[0],
            "tags_id_list": parse_tags_string(row[1]) # Trả về dạng [7, 19, 230]
        })
    
    conn.close()
    return as_tags, ls_tags, active_skills_sample, leader_skills_sample

def main():
    try:
        # Bước 1: Thu thập metadata từ DB cục bộ
        as_tags, ls_tags, active_samples, leader_samples = fetch_db_metadata()
        
        # Bước 2: Xây dựng ngữ cảnh (Context) chi tiết gửi cho AI
        context = {
            "current_active_skill_tags_in_db": as_tags,
            "current_leader_skill_tags_in_db": ls_tags,
            "active_skills_examples": active_samples,
            "leader_skills_examples": leader_samples
        }
        
        prompt = f"""
        Bạn là một chuyên gia phân tích dữ liệu cao cấp cho tựa game Puzzle & Dragons (PAD).
        Dưới đây là cấu trúc dữ liệu kỹ năng thô hiện tại trích xuất từ database hệ thống:
        
        {json.dumps(context, indent=2)}
        
        Nhiệm vụ của bạn:
        1. Phân tích văn bản tiếng Anh (`desc_en`) của cả Active Skills và Leader Skills. Lưu ý rằng tên `name_en` trong bảng tags hiện tại chỉ là tên gọi quen thuộc của cộng đồng, nó có thể không khớp trực tiếp từ chữ với chuỗi hội thoại thực tế trong `desc_en`.
        2. Sinh ra chuỗi Regex Python (`regex_pattern`) chuẩn xác nhất để khớp với các cụm từ hiệu ứng trong `desc_en` thực tế:
           - Sử dụng `(\\d+)` hoặc `(\\d+\\.?\\d*)` để bắt các giá trị số động (số lượt turn, số combo, phần trăm giảm sát thương, tỷ lệ nhân chỉ số).
           - Viết regex ở dạng không phân biệt hoa thường nếu cần, đảm bảo bóc tách được các giá trị số cốt lõi.
        3. Đối với các hiệu ứng mới xuất hiện trong danh sách mẫu `desc_en` nhưng CHƯA CÓ trong danh mục tags cũ (`status`: 'new_effect_detected'):
           - Tự đề xuất một `tag_name_en` mới viết dưới dạng snake_case.
           - Để trường `tag_id` là null.
           - Viết Regex tương ứng cho hiệu ứng mới đó.
        """
        
        print(f"🚀 Đang gửi dữ liệu phân tích sang Gemini 2.5 Flash...")
        
        # Bước 3: Gọi API Gemini 2.5 Flash với cấu hình Structured Output (JSON)
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=PatternMigrationSchema,
                temperature=0.1  # Giữ nhiệt độ thấp để sinh Regex chuẩn xác logic, không sáng tạo tùy tiện
            )
        )
        
        # Bước 4: Lưu kết quả đầu ra
        output_path = "data/pad_generated_patterns.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Thư viện json.loads sẽ tự động gỡ các escape char dư thừa từ AI trả về
        final_data = json.loads(response.text)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=4, ensure_ascii=False)
            
        print(f"✨ Xử lý thành công! Bộ quy tắc Regex đã được xuất ra file: {output_path}")
        print(f"📊 Tìm thấy tổng cộng {len(final_data['patterns'])} mẫu ánh xạ kỹ năng.")
        
    except sqlite3.OperationalError as db_err:
        print(f"❌ Lỗi Database: Không thể đọc file SQLite tại '{SQLITE_DB_PATH}'. Kiểm tra lại đường dẫn. Chi tiết: {db_err}")
    except Exception as e:
        print(f"💥 Lỗi hệ thống trong quá trình xử lý di trú: {e}")

if __name__ == "__main__":
    main()