import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
import logging

# --- Cấu hình logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Load API key (Chỉ chạy 1 lần khi module được import) ---
try:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.warning("GEMINI_API_KEY không tìm thấy trong .env. Đang thử biến môi trường...")
        api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key:
        genai.configure(api_key=api_key)
        logging.info("Đã cấu hình Gemini API Key.")
    else:
        logging.error("Không thể tìm thấy GEMINI_API_KEY. Vui lòng kiểm tra file .env hoặc biến môi trường.")
        # Bạn có thể muốn raise Exception ở đây nếu API key là bắt buộc
        # raise ValueError("Không tìm thấy GEMINI_API_KEY")

except Exception as e:
    logging.error(f"Lỗi khi cấu hình .env hoặc Gemini: {e}")

# --- 1. HÀM CHÍNH ĐỂ TẠO KẾ HOẠCH ---

def create_trip_plan_from_file(places_input_filepath: str, user_location_dict: dict, requested_duration_text: str):
    """
    Tạo kế hoạch du lịch từ file JSON địa điểm, vị trí người dùng, và thời gian mong muốn.
    Trả về đường dẫn file kế hoạch (str) nếu thành công, ngược lại trả về None.
    """
    
    try:
        input_path = Path(places_input_filepath)
        if not input_path.exists():
            logging.error(f"File input không tồn tại: {places_input_filepath}")
            return None

        # --- 1.1. ĐỊNH NGHĨA ĐƯỜNG DẪN OUTPUT ---
        output_dir = Path("json/GeminiAPIResponse")
        output_file_name = f"{input_path.stem}_geminiAPI.json"
        output_file_path = output_dir / output_file_name

        # --- 1.2. TỰ ĐỘNG TẠO THƯ MỤC OUTPUT ---
        output_dir.mkdir(parents=True, exist_ok=True)

        # --- 1.3. Load dữ liệu địa điểm ---
        logging.info(f"Đang đọc file input: {input_path}")
        with open(input_path, "r", encoding="utf-8") as f:
            places_data = json.load(f)
        
        if not places_data:
            logging.warning(f"File input {input_path} không có dữ liệu.")
            return None

    except Exception as e:
        logging.error(f"Lỗi khi đọc file hoặc xử lý đường dẫn: {e}")
        return None

    # --- 2. ĐỊNH NGHĨA PROMPT (với tham số) ---
    
    # Sử dụng f-string để truyền biến dễ dàng hơn
    prompt = f"""
Bạn là một hướng dẫn viên du lịch thông minh.

Người dùng hiện ở vị trí {user_location_dict}.
Dữ liệu địa điểm (nhà hàng, công viên, viện bảo tàng, quán cafe, điểm du lịch) được cung cấp bên dưới.

Nhiệm vụ:
- Tạo **1 kế hoạch mini trip** với tổng thời gian là: **{requested_duration_text}**.
- Lên lịch có trình tự hợp lý như: 
  ăn → tham quan → cafe/đi dạo → ăn nhẹ hoặc quay về gần chỗ nghỉ.
- Ưu tiên chọn địa điểm có đánh giá tốt (rating >= 3.0).
- Ước lượng thời gian di chuyển giữa các điểm (AI có thể ước lượng).
- Gợi ý phương tiện phù hợp: đi bộ, tàu, hoặc xe máy/ô tô.
- Thêm mô tả ngắn gọn và lý do chọn mỗi địa điểm.
- Không được lặp lại địa điểm, ví dụ: địa điểm 3 và 4 không đc trùng lặp
- Ngôn ngữ của phần mô tả là tiếng Nhật.
- Với mỗi địa điểm, hãy trả về **TẤT CẢ** giá trị trong `photo_references` (nếu có).

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
      "photo_references": ["string", "string", ...]
    }}
  ],
  "summary": "string"
}}
"""

    # --- 3. ĐỊNH NGHĨA CẤU HÌNH GENERATION ---
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
                            # === SỬA LỖI QUAN TRỌNG ===
                            # Input của bạn là 1 danh sách, nên output cũng phải là danh sách
                            "photo_references": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                            # === KẾT THÚC SỬA LỖI ===
                        },
                        "required": [
                            "order", "name", "activity", "location",
                            "info", "distance_text", "duration_text", "transport_mode",
                            "photo_references" # Thêm vào đây để đảm bảo AI luôn trả về
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

    # --- 4. GỌI MODEL ---
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", # Nâng cấp lên 1.5-flash cho nhanh và tốt
            generation_config=generation_config
        )

        logging.info("Đang gọi Gemini API để tạo kế hoạch...")
        # Chỉ gửi 20 địa điểm đầu tiên để tiết kiệm token và tránh vượt quá giới hạn
        response = model.generate_content(
            f"{prompt}\n\nDữ liệu địa điểm:\n{json.dumps(places_data[:20], ensure_ascii=False)}"
        )

        # response.text là JSON string
        result_json = json.loads(response.text)

        # --- 5. GHI FILE VÀ TRẢ VỀ ---
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(result_json, f, ensure_ascii=False, indent=4)

        logging.info(f"Đã lưu kế hoạch vào file: {output_file_path.absolute()}")
        
        # Trả về đường dẫn tuyệt đối của file đã lưu
        return str(output_file_path.absolute())

    except Exception as e:
        logging.error(f"Lỗi khi gọi Gemini API hoặc lưu file: {e}")
        if "response" in locals():
            logging.error(f"Phản hồi lỗi từ API (nếu có): {response.prompt_feedback}")
        return None

# --- 6. KHỐI __main__ ĐỂ TEST ---
# (Chỉ chạy khi bạn chạy trực tiếp file gemini_planner.py)
if __name__ == "__main__":
    logging.info("--- CHẠY TEST (standalone) cho gemini_planner.py ---")
    
    # Giả lập các giá trị đầu vào
    test_input_file = "json/test/MinimalSearch_pref_ramen_pref_park_pref_museum_art_20251028_143155.json"
    test_location = {"lat": 34.6872571, "lng": 135.50}
    test_duration = "khoảng 3-4 tiếng, bắt đầu từ buổi trưa"

    # Kiểm tra xem file test có tồn tại không
    if not Path(test_input_file).exists():
        logging.warning(f"File test '{test_input_file}' không tìm thấy.")
        logging.warning("Đang tạo một file giả lập...")
        
        test_input_dir = Path("json/test")
        test_input_dir.mkdir(parents=True, exist_ok=True)
        test_data = [
            {
                "place_id": "ChIJN5X_p83nAGARqNAvKzI3ENI",
                "location": {"lat": 34.6937378, "lng": 135.5021651},
                "types": ["restaurant", "food", "point_of_interest", "establishment"],
                "rating": 4.5,
                "user_ratings_total": 5000,
                "name": "Ichiran Ramen Umeda",
                "photo_references": ["ref1_ABC", "ref2_XYZ"]
            },
            {
                "place_id": "ChIJexdJkNDnAGAR_P9Vn1hGkPY",
                "location": {"lat": 34.685361, "lng": 135.526225},
                "types": ["park", "tourist_attraction", "point_of_interest", "establishment"],
                "rating": 4.4,
                "user_ratings_total": 12000,
                "name": "Osaka Castle Park",
                "photo_references": ["ref3_123", "ref4_456"]
            }
        ]
        with open(test_input_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=4)
        logging.info(f"Đã tạo file giả lập: {test_input_file}")

    # Gọi hàm chính
    saved_plan_path = create_trip_plan_from_file(
        test_input_file,
        test_location,
        test_duration
    )
    
    if saved_plan_path:
        logging.info(f"\n--- TEST HOÀN THÀNH. File kế hoạch đã lưu tại: {saved_plan_path} ---")
    else:
        logging.error("\n--- TEST THẤT BẠI. Không có file kế hoạch nào được tạo. ---")