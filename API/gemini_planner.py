# import os
# import json
# # import from dotenv load_dotenv # <-- ĐÃ XÓA
# import google.generativeai as genai
# from pathlib import Path
# import logging

# # --- Cấu hình logging ---
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# # --- 1. Load API key (GIỮ NGUYÊN BẢN HARDCODE CỦA BẠN) ---
# try:
#     # load_dotenv() # <-- Đã xóa
    
#     # Gán key trực tiếp (Theo yêu cầu của bạn)
#     api_key = "AIzaSyAHp23fhppO9RHgnhstQNe3V6s4P-SbePw" # <--- GIỮ NGUYÊN KEY CỦA BẠN
    
#     if api_key: 
#         genai.configure(api_key=api_key)
#         logging.info("Đã cấu hình Gemini API Key (từ code trực tiếp).")
#     else:
#         logging.error("Không thể tìm thấy GEMINI_API_KEY. Vui lòng kiểm tra code.")
#         raise EnvironmentError("GEMINI_API_KEY không được đặt.")

# except Exception as e:
#     logging.error(f"Lỗi khi cấu hình .env hoặc Gemini: {e}")

# # --- 2. HÀM MỚI: "SƠ CHẾ" DỮ LIỆU GỬI LÊN ---

# def preprocess_data_for_gemini(original_data: list) -> list:
#     """
#     Tạo "file ảo" (danh sách nhẹ) để gửi cho Gemini.
#     Loại bỏ "photo_references" và "review_texts" để tiết kiệm token.
#     """
#     lightweight_data = []
#     for place in original_data:
#         if not isinstance(place, dict): continue
        
#         light_place = {
#             "place_id": place.get("place_id"),
#             "name": place.get("name"), 
#             "location": place.get("location"),
#             "types": place.get("types"),
#             "rating": place.get("rating"),
#             "user_ratings_total": place.get("user_ratings_total"),
#             "price_level": place.get("price_level")
#             # "photo_references" và "review_texts" đã bị cố tình loại bỏ
#         }
#         lightweight_data.append(light_place)
#     return lightweight_data

# # --- 3. HÀM MỚI: TẠO BẢN ĐỒ TRA CỨU ĐỂ "LÀM GIÀU" ---

# def create_lookup_maps(original_data: list) -> (dict, dict):
#     """
#     Tạo 2 bản đồ (dictionary) để tra cứu nhanh photo_references và review_texts
#     dựa trên place_id.
#     """
#     photo_lookup = {}
#     review_lookup = {}
    
#     for place in original_data:
#         if not isinstance(place, dict): continue
        
#         place_id = place.get("place_id")
#         if place_id:
#             photo_lookup[place_id] = place.get("photo_references", [])
#             review_lookup[place_id] = place.get("review_texts", [])
            
#     return photo_lookup, review_lookup

# # --- 4. HÀM MỚI: "LÀM GIÀU" KẾ HOẠCH BẰNG DỮ LIỆU GỐC ---

# def enrich_plans_with_details(plans: list, photo_lookup: dict, review_lookup: dict) -> list:
#     """
#     Duyệt qua các kế hoạch do Gemini trả về và "bơm" (enrich)
#     photo_references và review_texts vào lại.
#     """
#     # Duyệt qua từng kế hoạch trong danh sách [plan1, plan2, plan3]
#     for plan in plans:
#         if "waypoints" not in plan or not isinstance(plan["waypoints"], list):
#             continue
            
#         # Duyệt qua từng địa điểm trong kế hoạch
#         for waypoint in plan["waypoints"]:
#             place_id = waypoint.get("place_id")
            
#             if place_id:
#                 # Dùng place_id để tra cứu từ bản đồ
#                 waypoint["photo_references"] = photo_lookup.get(place_id, [])
#                 waypoint["review_texts"] = review_lookup.get(place_id, []) # <-- Bơm cả review
                
#     return plans

# # --- 5. HÀM CHÍNH ĐỂ TẠO KẾ HOẠCH (ĐÃ CẬP NHẬT) ---

# def create_trip_plan_from_file(places_input_filepath: str, user_location_dict: dict, requested_duration_text: str):
#     """
#     Tạo 3 kế hoạch du lịch, triển khai chiến lược "Sơ chế -> Gửi -> Làm giàu".
#     """
    
#     try:
#         input_path = Path(places_input_filepath)
#         if not input_path.exists():
#             logging.error(f"File input không tồn tại: {places_input_filepath}")
#             return None

#         # --- 5.1. ĐỊNH NGHĨA ĐƯỜNG DẪN OUTPUT ---
#         output_dir = Path("json/GeminiAPIResponse")
#         output_file_name = f"{input_path.stem}_geminiAPI_Enriched.json" # Đổi tên file
#         output_file_path = output_dir / output_file_name
#         output_dir.mkdir(parents=True, exist_ok=True)

#         # --- 5.2. Load và Sơ chế dữ liệu (CHIẾN LƯỢC MỚI) ---
#         logging.info(f"Đang đọc file input: {input_path}")
#         with open(input_path, "r", encoding="utf-8") as f:
#             original_places_data = json.load(f)
        
#         if not original_places_data:
#             logging.warning(f"File input {input_path} không có dữ liệu.")
#             return None

#         # Bước 1: Tạo "file ảo" (dữ liệu nhẹ) để gửi cho Gemini
#         lightweight_data = preprocess_data_for_gemini(original_places_data)
        
#         # *** SỬA LỖI SYNTAX Ở ĐÂY ***
#         logging.info(f"Đã 'sơ chế' {len(original_places_data)} địa điểm thành dữ liệu nhẹ.")
        
#         # Bước 2: Tạo bản đồ tra cứu để "làm giàu" sau
#         photo_lookup, review_lookup = create_lookup_maps(original_places_data)
#         logging.info("Đã tạo bản đồ tra cứu (lookup maps) cho ảnh và review.")

#     except Exception as e:
#         logging.error(f"Lỗi khi đọc file hoặc xử lý đường dẫn: {e}")
#         return None

#     # --- 5.3. ĐỊNH NGHĨA PROMPT (ĐÃ CẬP NHẬT) ---
    
#     prompt = f"""
# Bạn là một hướng dẫn viên du lịch thông minh.

# Người dùng hiện ở vị trí {user_location_dict}.
# Dữ liệu địa điểm (nhà hàng, công viên, quán cafe, v.v.) được cung cấp bên dưới.

# NhiệmVụ:
# - Tạo ** 3 kế hoạch mini trip khác nhau** với tổng thời gian mỗi kế hoạch là: **{requested_duration_text}**.
# - Lên lịch có trình tự hợp lý (ăn → tham quan → cafe, v.v.).
# - Ưu tiên chọn địa điểm có đánh giá tốt (rating >= 3.0).
# - Ước lượng thời gian di chuyển và gợi ý phương tiện.
# - Thêm mô tả ngắn gọn (tiếng Nhật) và lý do chọn mỗi địa điểm.
# - **Quan trọng:** Với mỗi địa điểm trong `waypoints`, hãy chắc chắn trả về `place_id` của nó.
# - Không được lặp lại địa điểm.

# Kết quả trả về dưới dạng JSON theo schema đã định nghĩa.
# """

#     # --- 5.4. ĐỊNH NGHĨA CẤU HÌNH GENERATION (ĐÃ CẬP NHẬT) ---
    
#     single_plan_schema = {
#         "type": "object",
#         "properties": {
#             "plan_title": {"type": "string"},
#             "theme": {"type": "string"},
#             "estimated_duration_hours": {"type": "number"},
#             "waypoints": {
#                 "type": "array",
#                 "items": {
#                     "type": "object",
#                     "properties": {
#                         # === THAY ĐỔI QUAN TRỌNG ===
#                         "place_id": {"type": "string"}, # Đây là trường bắt buộc
#                         # ==========================
#                         "order": {"type": "integer"},
#                         "name": {"type": "string"},
#                         "activity": {"type": "string"},
#                         "location": {
#                             "type": "object",
#                             "properties": {
#                                 "lat": {"type": "number"},
#                                 "lng": {"type": "number"}
#                             },
#                             "required": ["lat", "lng"]
#                         },
#                         "info": {"type": "string"},
#                         "distance_text": {"type": "string"},
#                         "duration_text": {"type": "string"},
#                         "transport_mode": {"type": "string"}
#                         # === ĐÃ LOẠI BỎ "photo_references" khỏi đây ===
#                     },
#                     "required": [
#                         # === THAY ĐỔI QUAN TRỌNG ===
#                         "place_id", # Bắt buộc Gemini trả về
#                         # ==========================
#                         "order", "name", "activity", "location",
#                         "info", "distance_text", "duration_text", "transport_mode"
#                         # === ĐÃ LOẠI BỎ "photo_references" khỏi required ===
#                     ]
#                 }
#             },
#             "summary": {"type": "string"}
#         },
#         "required": [
#             "plan_title", "theme", "estimated_duration_hours",
#             "waypoints", "summary"
#         ]
#     }

#     generation_config = {
#         "response_mime_type": "application/json",
#         "response_schema": {
#             "type": "array",
#             "items": single_plan_schema
#         }
#     }

#     # --- 5.5. GỌI MODEL VÀ "LÀM GIÀU" KẾT QUẢ ---
#     try:
#         model = genai.GenerativeModel(
#             model_name="gemini-2.5-flash", 
#             generation_config=generation_config
#         )

#         logging.info("Đang gọi Gemini API với dữ liệu đã sơ chế...")
        
#         # Bước 3: Gửi dữ liệu NHẸ (lightweight_data) cho Gemini
#         response = model.generate_content(
#             f"{prompt}\n\nDữ liệu địa điểm:\n{json.dumps(lightweight_data, ensure_ascii=False)}"
#         )

#         # Gemini trả về kế hoạch (chưa có ảnh/review)
#         plans_from_gemini = json.loads(response.text)

#         # Bước 4: "Làm giàu" (Enrich) kế hoạch bằng bản đồ tra cứu
#         logging.info("Gemini đã trả về. Đang 'làm giàu' dữ liệu với ảnh và review...")
#         enriched_plans = enrich_plans_with_details(
#             plans_from_gemini, 
#             photo_lookup, 
#             review_lookup
#         )

#         # --- 5.6. GHI FILE VÀ TRẢ VỀ ---
#         with open(output_file_path, "w", encoding="utf-8") as f:
#             # Lưu kế hoạch ĐÃ ĐƯỢC LÀM GIÀU (enriched_plans)
#             json.dump(enriched_plans, f, ensure_ascii=False, indent=4)

#         logging.info(f"Đã lưu kế hoạch (đã làm giàu) vào file: {output_file_path.absolute()}")
        
#         return str(output_file_path.absolute())

#     except Exception as e:
#         logging.error(f"Lỗi khi gọi Gemini API hoặc 'làm giàu' file: {e}")
#         if "response" in locals() and hasattr(response, 'prompt_feedback'):
#             logging.error(f"Phản hồi lỗi từ API (nếu có): {response.prompt_feedback}")
#         return None

# # --- 6. KHỐI __main__ ĐỂ TEST ---
# if __name__ == "__main__":
#     logging.info("--- CHẠY TEST (standalone) cho gemini_planner.py ---")
    
#     test_input_file = "json/test/MinimalSearch_pref_ramen_pref_park_pref_museum_art_20251028_143155.json"
#     test_location = {"lat": 34.6872571, "lng": 151.10} # <--- Sửa một giá trị để test
#     test_duration = "khoảng 3-4 tiếng, bắt đầu từ buổi trưa"

#     if not Path(test_input_file).exists():
#         logging.warning(f"File test '{test_input_file}' không tìm thấy. Đang tạo file giả lập...")
        
#         test_input_dir = Path("json/test")
#         test_input_dir.mkdir(parents=True, exist_ok=True)
#         test_data = [
#             {
#                 "place_id": "ChIJN5X_p83nAGARqNAvKzI3ENI",
#                 "location": {"lat": 34.6937378, "lng": 135.5021651},
#                 "types": ["restaurant", "food"],
#                 "rating": 4.5, "user_ratings_total": 5000,
#                 "name": "Ichiran Ramen Umeda",
#                 "photo_references": ["ref1_ABC", "ref2_XYZ"],
#                 "review_texts": ["Review 1...", "Review 2..."]
#             },
#             {
#                 "place_id": "ChIJexdJkNDnAGAR_P9Vn1hGkPY",
#                 "location": {"lat": 34.685361, "lng": 135.526225},
#                 "types": ["park", "tourist_attraction"],
#                 "rating": 4.4, "user_ratings_total": 12000,
#                 "name": "Osaka Castle Park",
#                 "photo_references": ["ref3_123", "ref4_456"],
#                 "review_texts": ["Review 3...", "Review 4..."]
#             }
#         ]
#         with open(test_input_file, "w", encoding="utf-8") as f:
#             json.dump(test_data, f, indent=4)
#         logging.info(f"Đã tạo file giả lập: {test_input_file}")

#     # Gọi hàm chính
#     saved_plan_path = create_trip_plan_from_file(
#         test_input_file,
#         test_location,
#         test_duration
#     )
    
#     if saved_plan_path:
#         logging.info(f"\n--- TEST HOÀN THÀNH. File kế hoạch đã lưu tại: {saved_plan_path} ---")
#     else:
#         logging.error("\n--- TEST THẤT BẠI. Không có file kế hoạch nào được tạo. ---")

# 22222222222222222222222222222
# import os
# import json
# # import from dotenv load_dotenv # <-- ĐÃ XÓA
# import google.generativeai as genai
# from pathlib import Path
# import logging

# # --- Cấu hình logging ---
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# # --- 1. Load API key (GIỮ NGUYÊN BẢN HARDCODE CỦA BẠN) ---
# try:
#     # load_dotenv() # <-- Đã xóa
    
#     # Gán key trực tiếp (Theo yêu cầu của bạn)
#     api_key = "AIzaSyCHAV26v44x6YqeuclZZ1I4RquRr9Nk6bQ" # <--- GIỮ NGUYÊN KEY CỦA BẠN
    
#     if api_key: 
#         genai.configure(api_key=api_key)
#         logging.info("Đã cấu hình Gemini API Key (từ code trực tiếp).")
#     else:
#         logging.error("Không thể tìm thấy GEMINI_API_KEY. Vui lòng kiểm tra code.")
#         raise EnvironmentError("GEMINI_API_KEY không được đặt.")

# except Exception as e:
#     logging.error(f"Lỗi khi cấu hình .env hoặc Gemini: {e}")

# # --- 2. HÀM MỚI: "SƠ CHẾ" DỮ LIỆU GỬI LÊN ---

# def preprocess_data_for_gemini(original_data: list) -> list:
#     """
#     Tạo "file ảo" (danh sách nhẹ) để gửi cho Gemini.
#     Loại bỏ "photo_references" và "review_texts" để tiết kiệm token.
#     """
#     lightweight_data = []
#     for place in original_data:
#         if not isinstance(place, dict): continue
        
#         light_place = {
#             "place_id": place.get("place_id"),
#             "name": place.get("name"), 
#             "location": place.get("location"),
#             "types": place.get("types"),
#             "rating": place.get("rating"),
#             "user_ratings_total": place.get("user_ratings_total"),
#             "price_level": place.get("price_level")
#             # "photo_references" và "review_texts" đã bị cố tình loại bỏ
#         }
#         lightweight_data.append(light_place)
#     return lightweight_data

# # --- 3. HÀM MỚI: TẠO BẢN ĐỒ TRA CỨU ĐỂ "LÀM GIÀU" ---

# def create_lookup_maps(original_data: list) -> (dict, dict):
#     """
#     Tạo 2 bản đồ (dictionary) để tra cứu nhanh photo_references và review_texts
#     dựa trên place_id.
#     """
#     photo_lookup = {}
#     review_lookup = {}
    
#     for place in original_data:
#         if not isinstance(place, dict): continue
        
#         place_id = place.get("place_id")
#         if place_id:
#             photo_lookup[place_id] = place.get("photo_references", [])
#             review_lookup[place_id] = place.get("review_texts", [])
            
#     return photo_lookup, review_lookup

# # --- 4. HÀM MỚI: "LÀM GIÀU" KẾ HOẠCH BẰNG DỮ LIỆU GỐC ---

# def enrich_plans_with_details(plans: list, photo_lookup: dict, review_lookup: dict) -> list:
#     """
#     Duyệt qua các kế hoạch do Gemini trả về và "bơm" (enrich)
#     photo_references và review_texts vào lại.
#     """
#     # Duyệt qua từng kế hoạch trong danh sách [plan1, plan2, plan3]
#     for plan in plans:
#         if "waypoints" not in plan or not isinstance(plan["waypoints"], list):
#             continue
            
#         # Duyệt qua từng địa điểm trong kế hoạch
#         for waypoint in plan["waypoints"]:
#             place_id = waypoint.get("place_id")
            
#             if place_id:
#                 # Dùng place_id để tra cứu từ bản đồ
#                 waypoint["photo_references"] = photo_lookup.get(place_id, [])
#                 waypoint["review_texts"] = review_lookup.get(place_id, []) # <-- Bơm cả review
                
#     return plans

# # --- 5. HÀM CHÍNH ĐỂ TẠO KẾ HOẠCH (ĐÃ CẬP NHẬT) ---

# def create_trip_plan_from_file(places_input_filepath: str, user_location_dict: dict, requested_duration_text: str):
#     """
#     Tạo 3 kế hoạch du lịch, triển khai chiến lược "Sơ chế -> Gửi -> Làm giàu".
#     """
    
#     try:
#         input_path = Path(places_input_filepath)
#         if not input_path.exists():
#             logging.error(f"File input không tồn tại: {places_input_filepath}")
#             return None

#         # --- 5.1. ĐỊNH NGHĨA ĐƯỜNG DẪN OUTPUT ---
#         output_dir = Path("json/GeminiAPIResponse")
#         output_file_name = f"{input_path.stem}_geminiAPI_Enriched.json" # Đổi tên file
#         output_file_path = output_dir / output_file_name
#         output_dir.mkdir(parents=True, exist_ok=True)

#         # --- 5.2. Load và Sơ chế dữ liệu (CHIẾN LƯỢC MỚI) ---
#         logging.info(f"Đang đọc file input: {input_path}")
#         with open(input_path, "r", encoding="utf-8") as f:
#             original_places_data = json.load(f)
        
#         if not original_places_data:
#             logging.warning(f"File input {input_path} không có dữ liệu.")
#             return None

#         # Bước 1: Tạo "file ảo" (dữ liệu nhẹ) để gửi cho Gemini
#         lightweight_data = preprocess_data_for_gemini(original_places_data)
        
#         # *** SỬA LỖI SYNTAX Ở ĐÂY ***
#         logging.info(f"Đã 'sơ chế' {len(original_places_data)} địa điểm thành dữ liệu nhẹ.")
        
#         # Bước 2: Tạo bản đồ tra cứu để "làm giàu" sau
#         photo_lookup, review_lookup = create_lookup_maps(original_places_data)
#         logging.info("Đã tạo bản đồ tra cứu (lookup maps) cho ảnh và review.")

#     except Exception as e:
#         logging.error(f"Lỗi khi đọc file hoặc xử lý đường dẫn: {e}")
#         return None

#     # --- 5.3. ĐỊNH NGHĨA PROMPT (ĐÃ CẬP NHẬT) ---
    
#     # === THAY ĐỔI CHÍNH Ở ĐÂY ===
#     # Đã làm rõ yêu cầu về 'requested_duration_text'
#     prompt = f"""
# Bạn là một hướng dẫn viên du lịch thông minh.

# Người dùng hiện ở vị trí {user_location_dict}.
# Dữ liệu địa điểm (nhà hàng, công viên, quán cafe, v.v.) được cung cấp bên dưới.

# NhiệmVụ:
# - Tạo ** 3 kế hoạch mini trip khác nhau**.
# - **Yêu cầu về thời gian:** Người dùng mô tả thời gian họ có là: **"{requested_duration_text}"**.
# - Dựa trên mô tả này, hãy thiết kế các kế hoạch cho phù hợp (ví dụ: nếu họ nói 'bao gồm bữa trưa', hãy thêm 1 nhà hàng).
# - **Quan trọng:** Dù người dùng mô tả bằng (string), bạn phải tự ước lượng tổng thời gian (ví dụ: 4.5) và điền nó dưới dạng một **con số (number)** vào trường `estimated_duration_hours`.
# - Lên lịch có trình tự hợp lý (ăn → tham quan → cafe, v.v.).
# - Ưu tiên chọn địa điểm có đánh giá tốt (rating >= 3.0).
# - Ước lượng thời gian di chuyển và gợi ý phương tiện.
# - Thêm mô tả ngắn gọn (tiếng Nhật) và lý do chọn mỗi địa điểm.
# - **Quan trọng:** Với mỗi địa điểm trong `waypoints`, hãy chắc chắn trả về `place_id` của nó.
# - Không được lặp lại địa điểm.

# Kết quả trả về dưới dạng JSON theo schema đã định nghĩa.
# """
#     # === KẾT THÚC THAY ĐỔI ===

#     # --- 5.4. ĐỊNH NGHĨA CẤU HÌNH GENERATION (Giữ nguyên) ---
    
#     single_plan_schema = {
#         "type": "object",
#         "properties": {
#             "plan_title": {"type": "string"},
#             "theme": {"type": "string"},
#             "estimated_duration_hours": {"type": "number"}, # <-- Giữ nguyên là number
#             "waypoints": {
#                 "type": "array",
#                 "items": {
#                     "type": "object",
#                     "properties": {
#                         "place_id": {"type": "string"}, 
#                         "order": {"type": "integer"},
#                         "name": {"type": "string"},
#                         "activity": {"type": "string"},
#                         "location": {
#                             "type": "object",
#                             "properties": {
#                                 "lat": {"type": "number"},
#                                 "lng": {"type": "number"}
#                             },
#                             "required": ["lat", "lng"]
#                         },
#                         "info": {"type": "string"},
#                         "distance_text": {"type": "string"},
#                         "duration_text": {"type": "string"},
#                         "transport_mode": {"type": "string"}
#                     },
#                     "required": [
#                         "place_id", 
#                         "order", "name", "activity", "location",
#                         "info", "distance_text", "duration_text", "transport_mode"
#                     ]
#                 }
#             },
#             "summary": {"type": "string"}
#         },
#         "required": [
#             "plan_title", "theme", "estimated_duration_hours",
#             "waypoints", "summary"
#         ]
#     }

#     generation_config = {
#         "response_mime_type": "application/json",
#         "response_schema": {
#             "type": "array",
#             "items": single_plan_schema
#         }
#     }

#     # --- 5.5. GỌI MODEL VÀ "LÀM GIÀU" KẾT QUẢ ---
#     try:
#         model = genai.GenerativeModel(
#             model_name="gemini-2.5-flash", 
#             generation_config=generation_config
#         )

#         logging.info("Đang gọi Gemini API với dữ liệu đã sơ chế...")
        
#         # Bước 3: Gửi dữ liệu NHẸ (lightweight_data) cho Gemini
#         # Thêm timeout (120 giây) để tránh bị treo
#         response = model.generate_content(
#             f"{prompt}\n\nDữ liệu địa điểm:\n{json.dumps(lightweight_data, ensure_ascii=False)}",
#             request_options={'timeout': 120} 
#         )

#         # Gemini trả về kế hoạch (chưa có ảnh/review)
#         plans_from_gemini = json.loads(response.text)

#         # Bước 4: "Làm giàu" (Enrich) kế hoạch bằng bản đồ tra cứu
#         logging.info("Gemini đã trả về. Đang 'làm giàu' dữ liệu với ảnh và review...")
#         enriched_plans = enrich_plans_with_details(
#             plans_from_gemini, 
#             photo_lookup, 
#             review_lookup
#         )

#         # --- 5.6. GHI FILE VÀ TRẢ VỀ ---
#         with open(output_file_path, "w", encoding="utf-8") as f:
#             # Lưu kế hoạch ĐÃ ĐƯỢC LÀM GIÀU (enriched_plans)
#             json.dump(enriched_plans, f, ensure_ascii=False, indent=4)

#         logging.info(f"Đã lưu kế hoạch (đã làm giàu) vào file: {output_file_path.absolute()}")
        
#         return str(output_file_path.absolute())

#     except Exception as e:
#         logging.error(f"Lỗi khi gọi Gemini API hoặc 'làm giàu' file: {e}")
#         if "response" in locals() and hasattr(response, 'prompt_feedback'):
#             logging.error(f"Phản hồi lỗi từ API (nếu có): {response.prompt_feedback}")
#         return None

# # --- 6. KHỐI __main__ ĐỂ TEST ---
# if __name__ == "__main__":
#     logging.info("--- CHẠY TEST (standalone) cho gemini_planner.py ---")
    
#     test_input_file = "json/test/MinimalSearch_pref_ramen_pref_park_pref_museum_art_20251028_143155.json"
#     test_location = {"lat": 34.6872571, "lng": 151.10} 
    
#     # === THAY ĐỔI CHÍNH Ở ĐÂY ===
#     # Cập nhật test_duration để khớp với input mới từ frontend
#     test_duration = "khoảng 4-5 tiếng, bao gồm 1 bữa ăn trưa và 1 buổi cafe chiều"

#     if not Path(test_input_file).exists():
#         logging.warning(f"File test '{test_input_file}' không tìm thấy. Đang tạo file giả lập...")
        
#         test_input_dir = Path("json/test")
#         test_input_dir.mkdir(parents=True, exist_ok=True)
#         test_data = [
#             {
#                 "place_id": "ChIJN5X_p83nAGARqNAvKzI3ENI",
#                 "location": {"lat": 34.6937378, "lng": 135.5021651},
#                 "types": ["restaurant", "food"],
#                 "rating": 4.5, "user_ratings_total": 5000,
#                 "name": "Ichiran Ramen Umeda",
#                 "photo_references": ["ref1_ABC", "ref2_XYZ"],
#                 "review_texts": ["Review 1...", "Review 2..."]
#             },
#             {
#                 "place_id": "ChIJexdJkNDnAGAR_P9Vn1hGkPY",
#                 "location": {"lat": 34.685361, "lng": 135.526225},
#                 "types": ["park", "tourist_attraction"],
#                 "rating": 4.4, "user_ratings_total": 12000,
#                 "name": "Osaka Castle Park",
#                 "photo_references": ["ref3_123", "ref4_456"],
#                 "review_texts": ["Review 3...", "Review 4..."]
#             }
#         ]
#         with open(test_input_file, "w", encoding="utf-8") as f:
#             json.dump(test_data, f, indent=4)
#         logging.info(f"Đã tạo file giả lập: {test_input_file}")

#     # Gọi hàm chính
#     saved_plan_path = create_trip_plan_from_file(
#         test_input_file,
#         test_location,
#         test_duration
#     )
    
#     if saved_plan_path:
#         logging.info(f"\n--- TEST HOÀN THÀNH. File kế hoạch đã lưu tại: {saved_plan_path} ---")
#     else:
#         logging.error("\n--- TEST THẤT BẠI. Không có file kế hoạch nào được tạo. ---")


import os
import json
import google.generativeai as genai
from pathlib import Path
import logging

# --- Cấu hình logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. CONFIG KEY ---
try:
    # ⚠️ THAY KEY CỦA BẠN VÀO ĐÂY
    api_key = "AIzaSyCHOx76pYhevTejtc2mPWetXqYcARkg1Io" 
    
    if api_key: 
        genai.configure(api_key=api_key)
        logging.info("Đã cấu hình Gemini API Key.")
    else:
        raise EnvironmentError("GEMINI_API_KEY chưa được đặt.")
except Exception as e:
    logging.error(f"Lỗi cấu hình: {e}")

# --- 2. SƠ CHẾ DỮ LIỆU ---
def preprocess_data_for_gemini(original_data: list) -> list:
    lightweight_data = []
    for place in original_data:
        if not isinstance(place, dict): continue
        light_place = {
            "place_id": place.get("place_id"),
            "name": place.get("name"), 
            "location": place.get("location"),
            "types": place.get("types"),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("user_ratings_total"),
            "price_level": place.get("price_level")
        }
        lightweight_data.append(light_place)
    return lightweight_data

# --- 3. TẠO MAP TRA CỨU ---
def create_lookup_maps(original_data: list) -> (dict, dict):
    photo_lookup = {}
    review_lookup = {}
    for place in original_data:
        if not isinstance(place, dict): continue
        place_id = place.get("place_id")
        if place_id:
            photo_lookup[place_id] = place.get("photo_references", [])
            review_lookup[place_id] = place.get("review_texts", [])
    return photo_lookup, review_lookup

# --- 4. LÀM GIÀU DỮ LIỆU ---
def enrich_plans_with_details(plans: list, photo_lookup: dict, review_lookup: dict) -> list:
    for plan in plans:
        if "waypoints" not in plan or not isinstance(plan["waypoints"], list): continue
        for waypoint in plan["waypoints"]:
            place_id = waypoint.get("place_id")
            if place_id:
                waypoint["photo_references"] = photo_lookup.get(place_id, [])
                waypoint["review_texts"] = review_lookup.get(place_id, [])
    return plans

# --- 5. HÀM CHÍNH (TỐI ƯU HÓA TỐC ĐỘ) ---
def create_trip_plan_from_file(places_input_filepath: str, user_location_dict: dict, requested_duration_text: str):
    try:
        input_path = Path(places_input_filepath)
        if not input_path.exists(): return None

        # Output path
        output_dir = Path("json/GeminiAPIResponse")
        output_file_name = f"{input_path.stem}_geminiAPI_Enriched.json"
        output_file_path = output_dir / output_file_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Đọc dữ liệu
        with open(input_path, "r", encoding="utf-8") as f:
            original_places_data = json.load(f)
        
        if not original_places_data: return None

        # Sơ chế
        lightweight_data = preprocess_data_for_gemini(original_places_data)
        photo_lookup, review_lookup = create_lookup_maps(original_places_data)

        # --- PROMPT: CHỈ YÊU CẦU 1 PLAN ---
        # prompt = f"""
        # あなたはプロの旅行ガイドです。
        # ユーザーの現在地: {user_location_dict}
        # 希望所要時間: "{requested_duration_text}"
        
        # 以下の提供された場所データ（JSON）のみを使用して、最適な観光プランを **1つだけ** 作成してください。

        # 【要件】
        # 1. 移動順序が論理的で効率的であること。
        # 2. 各場所の `place_id` を必ず含めること。
        # 3. `estimated_duration_hours` は数値で出力すること（例: 4.5）。
        # 4. 出力言語は **日本語** です。
        # 5. `plan_title`（プラン名）、`theme`（テーマ）、`activity`（活動内容）、`info`（説明）、`summary`（概要）は魅力的で自然な日本語で記述してください。
        # """
        # # --- SCHEMA (GIỮ FORMAT ARRAY ĐỂ KHỚP CODE CŨ) ---
        # single_plan_schema = {
        #     "type": "object",
        #     "properties": {
        #         "plan_title": {"type": "string"},
        #         "theme": {"type": "string"},
        #         "estimated_duration_hours": {"type": "number"},
        #         "waypoints": {
        #             "type": "array",
        #             "items": {
        #                 "type": "object",
        #                 "properties": {
        #                     "place_id": {"type": "string"}, 
        #                     "order": {"type": "integer"},
        #                     "name": {"type": "string"},
        #                     "activity": {"type": "string"},
        #                     "location": {
        #                         "type": "object",
        #                         "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}}
        #                     },
        #                     "info": {"type": "string"},
        #                     "transport_mode": {"type": "string"}
        #                 },
        #                 "required": ["place_id", "order", "name", "location", "info"]
        #             }
        #         },
        #         "summary": {"type": "string"}
        #     },
        #     "required": ["plan_title", "waypoints", "estimated_duration_hours"]
        # }
        prompt = f"""
            あなたはプロの旅行ガイドです。
            ユーザーの現在地: {user_location_dict}
            希望所要時間: "{requested_duration_text}"
            
            以下の提供された場所データ（JSON）のみを使用して、最適な観光プランを **1つだけ** 作成してください。

            【要件】
            1. 移動順序が論理的で効率的であること。
            2. 各場所の `place_id` を必ず含めること。
            3. `estimated_duration_hours` は数値で出力すること（例: 4.5）。
            4. 出力言語は **日本語** です。
            5. `region_name` には、このプランの全スポットが含まれる「都市名」または「主要エリア名」を記入してください（例：新宿、大阪市、京都・嵐山）。
            6. `plan_title`、`theme`、`activity`、`info`、`summary`は魅力的で自然な日本語で記述してください。
            """

        single_plan_schema = {
            "type": "object",
            "properties": {
                # ▼▼▼ ここを追加 ▼▼▼
                "region_name": {
                    "type": "string", 
                    "description": "プラン全体が含まれる主要な都市名や地域名（例: 新宿区、大阪市、嵐山エリア）"
                },
                # ▲▲▲ ここまで ▲▲▲
                
                "plan_title": {"type": "string"},
                "theme": {"type": "string"},
                "estimated_duration_hours": {"type": "number"},
                "waypoints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "place_id": {"type": "string"}, 
                            "order": {"type": "integer"},
                            "name": {"type": "string"},
                            "activity": {"type": "string"},
                            "location": {
                                "type": "object",
                                "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}}
                            },
                            "info": {"type": "string"},
                            "transport_mode": {"type": "string"}
                        },
                        "required": ["place_id", "order", "name", "location", "info"]
                    }
                },
                "summary": {"type": "string"}
            },
            # ▼▼▼ requiredにも region_name を追加 ▼▼▼
            "required": ["region_name", "plan_title", "waypoints", "estimated_duration_hours"]
        }
        
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "array", # Vẫn trả về Array để Frontend dễ loop
                "items": single_plan_schema 
            }
        }

        # --- GỌI API (DÙNG FLASH 1.5 CHO NHANH) ---
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", # Flash cho tốc độ cao
            generation_config=generation_config
        )

        response = model.generate_content(
            f"{prompt}\n\nDữ liệu:\n{json.dumps(lightweight_data, ensure_ascii=False)}",
            request_options={'timeout': 60} 
        )

        plans_from_gemini = json.loads(response.text)

        # Nếu model trả về 1 object thay vì list, ta tự đóng gói vào list
        if isinstance(plans_from_gemini, dict):
            plans_from_gemini = [plans_from_gemini]
        
        # Chỉ lấy 1 plan đầu tiên (Double check)
        plans_from_gemini = plans_from_gemini[:1]

        # Làm giàu dữ liệu
        enriched_plans = enrich_plans_with_details(plans_from_gemini, photo_lookup, review_lookup)

        # Lưu file
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(enriched_plans, f, ensure_ascii=False, indent=4)

        return str(output_file_path.absolute())

    except Exception as e:
        logging.error(f"Lỗi: {e}")
        return None