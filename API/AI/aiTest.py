import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path  # <-- Thêm thư viện này

# --- Load API key ---
load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# --- 1. ĐỊNH NGHĨA ĐƯỜNG DẪN ---
# Chỉ cần thay đổi file input ở đây
input_file_path = Path(r"json/test/MinimalSearch_pref_ramen_pref_park_pref_museum_art_20251028_143155.json")

# Đường dẫn output sẽ tự động được tạo
output_dir = Path("json/GeminiAPIResponse")
output_file_name = f"{input_file_path.stem}_geminiAPI.json"
output_file_path = output_dir / output_file_name

# --- 2. TỰ ĐỘNG TẠO THƯ MỤC OUTPUT (nếu chưa có) ---
output_dir.mkdir(parents=True, exist_ok=True)

# --- Load dữ liệu địa điểm ---
print(f"Đang đọc file input: {input_file_path}")
with open(input_file_path, "r", encoding="utf-8") as f:
    places_data = json.load(f)


user_location = {"lat": 34.6872571, "lng": 135.50}

prompt = """
Bạn là một hướng dẫn viên du lịch thông minh.

Người dùng hiện ở vị trí {user_location}.
Dữ liệu địa điểm (nhà hàng, công viên, viện bảo tàng, quán cafe, điểm du lịch) được cung cấp bên dưới.

Nhiệm vụ:
- Tạo **1 kế hoạch mini trip** ngắn trong 3-6 tiếng.
- Lên lịch có trình tự hợp lý như: 
  ăn → tham quan → cafe/đi dạo → ăn nhẹ hoặc quay về gần chỗ nghỉ.
- Ưu tiên chọn địa điểm có đánh giá tốt (rating >= 3.0).
- Ước lượng thời gian di chuyển giữa các điểm (AI có thể ước lượng).
- Gợi ý phương tiện phù hợp: đi bộ, tàu, hoặc xe máy/ô tô.
- Thêm mô tả ngắn gọn và lý do chọn mỗi địa điểm.
- Tổng thời gian khoảng 3-6 tiếng.
- Giá trị photo_references thì phải trả về tất cả dưới, chứ không phải mỗi một giá trị đầu tiên
- Không được lặp lại địa điểm, ví dụ: địa điểm 3 và 4 không đc trùng lặp
- Ngôn ngữ của phần mô tả là tiếng Nhật
Kết quả trả về dưới dạng JSON để dùng trực tiếp cho Google Maps API.

Cấu trúc JSON:
{{
  "plan_title": "string",
  "theme": "string",
  "estimated_duration_hours": "number",
  "waypoints": [
    {{
      "order": "integer",
      "name": "string",
      "activity": "string",
      "location": {{ "lat": "number", "lng": "number" }},
      "info": "string",
      "distance_text": "string",
      "duration_text": "string",
      "transport_mode": "string",
      "photo_references":"string"
    }}
  ],
  "summary": "string"
}}
""".format(user_location=user_location)

generation_config = {
    "response_mime_type": "application/json",
    "response_schema": {
        "type": "object",
        "properties": {
            "plan_title": {"type": "string"},
            "theme": {"type": "string"},
            "estimated_duration_hours": {"type": "number"},
            "waypoints": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "order": {"type": "integer"},
                        "name": {"type": "string"},
                        "activity": {"type": "string"},
                        "location": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lng": {"type": "number"}
                            },
                            "required": ["lat", "lng"]
                        },
                        "info": {"type": "string"},
                        "distance_text": {"type": "string"},
                        "duration_text": {"type": "string"},
                        "transport_mode": {"type": "string"},
                        "photo_references": {"type": "string"}
                        
                    },
                    "required": [
                        "order", "name", "activity", "location",
                        "info", "distance_text", "duration_text", "transport_mode"
                    ]
                }
            },
            "summary": {"type": "string"}
        },
        "required": [
            "plan_title", "theme", "estimated_duration_hours",
            "waypoints", "summary"
        ]
    }
}

# --- Tạo model ---
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config
)

# --- Gọi AI ---
print("Đang gọi Gemini API để tạo kế hoạch...")
response = model.generate_content(
    f"{prompt}\n\nDữ liệu địa điểm:\n{json.dumps(places_data[:15], ensure_ascii=False)}"
)

# response.text là JSON string
result_json = json.loads(response.text)

# --- Ghi vào file riêng ---
with open(output_file_path, "w", encoding="utf-8") as f:
    json.dump(result_json, f, ensure_ascii=False, indent=4)

print(f"\n--- HOÀN THÀNH ---")
print(f"Đã lưu kế hoạch vào file:\n{output_file_path.absolute()}")