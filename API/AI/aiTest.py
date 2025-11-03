import os
import json 
from dotenv import load_dotenv
import google.generativeai as genai

# --- Load API key --- 
load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# --- Load dữ liệu địa điểm --- 
with open(r"json\test\MinimalSearch_pref_ramen_pref_park_pref_museum_art_20251028_143155.json", "r", encoding="utf-8") as f:
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
      "transport_mode": "string"
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
                        "transport_mode": {"type": "string"}
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
response = model.generate_content(
    f"{prompt}\n\nDữ liệu địa điểm:\n{json.dumps(places_data[:15], ensure_ascii=False)}" 
)

# response.text là JSON string
result_json = json.loads(response.text)

# Ghi vào file riêng
with open(r"json\output_gemini.json", "w", encoding="utf-8") as f:
    json.dump(result_json, f, ensure_ascii=False, indent=4)
