# Đây là file main_runner.py
# Đảm bảo file này nằm CÙNG THƯ MỤC với:
# - api_fetcher.py
# - gemini_planner.py
# - file .env của bạn

import api_fetcher
import gemini_planner  # <-- Import file mới
import time
import logging

# --- Cấu hình logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("--- BẮT ĐẦU CHƯƠG TRÌNH CHÍNH (main_runner.py) ---")

# --- 1. CẤU HÌNH ĐẦU VÀO CỦA BẠN ---

# Định nghĩa vị trí dưới dạng dictionary (để dùng cho Gemini)
NEW_USER_LOCATION_DICT = {"lat": 35.689487, "lng": 139.691711} # Ví dụ: Ga Tokyo

# Tự động tạo chuỗi string (để dùng cho Google Maps API)
NEW_USER_LOCATION_STRING = f"{NEW_USER_LOCATION_DICT['lat']},{NEW_USER_LOCATION_DICT['lng']}"

NEW_USER_RADIUS = 10000                      # Bán kính 10km
USER_PREFERENCES = ['pref_cafe', 'pref_sento', 'pref_bookstore']

# Biến thời gian MỚI mà bạn yêu cầu
NEW_TRIP_DURATION = "khoảng 4-5 tiếng, bao gồm 1 bữa ăn trưa và 1 buổi cafe chiều"

# --- 2. GỌI API GOOGLE MAPS (PHASE 1) ---

logging.info(f"Đang chuẩn bị tìm kiếm địa điểm cho: {USER_PREFERENCES}")
logging.info(f"Vị trí: {NEW_USER_LOCATION_STRING}, Bán kính: {NEW_USER_RADIUS}m")

start_total_time = time.time()
generated_maps_filepath = None
generated_plan_filepath = None

try:
    # Gọi hàm từ api_fetcher
    generated_maps_filepath = api_fetcher.run_search_and_save(
        USER_PREFERENCES,
        NEW_USER_LOCATION_STRING,
        NEW_USER_RADIUS
    )

    if generated_maps_filepath:
        logging.info(f"✅ Đã tìm và lưu địa điểm vào: {generated_maps_filepath}")
        
        # --- 3. GỌI API GEMINI (PHASE 2) ---
        # Chỉ chạy nếu Phase 1 thành công
        
        logging.info(f"\n--- Bắt đầu tạo kế hoạch với Gemini ---")
        logging.info(f"Input file: {generated_maps_filepath}")
        logging.info(f"Vị trí: {NEW_USER_LOCATION_DICT}")
        logging.info(f"Thời gian: {NEW_TRIP_DURATION}")
        
        # Gọi hàm từ gemini_planner
        generated_plan_filepath = gemini_planner.create_trip_plan_from_file(
            places_input_filepath=generated_maps_filepath,
            user_location_dict=NEW_USER_LOCATION_DICT,
            requested_duration_text=NEW_TRIP_DURATION
        )
        
        if generated_plan_filepath:
            logging.info(f"✅ Đã tạo và lưu kế hoạch vào: {generated_plan_filepath}")
        else:
            logging.error("❌ Lỗi khi tạo kế hoạch với Gemini.")

    else:
        logging.error("❌ KHÔNG THÀNH CÔNG (Google Maps API).")
        logging.warning("Không tìm thấy địa điểm, sẽ không chạy Gemini.")

except Exception as e:
    logging.critical(f"\n🔥🔥🔥 ĐÃ XẢY RA LỖI NGHIÊM TRỌNG TRONG main_runner: {e}", exc_info=True)


# --- 4. TỔNG KẾT ---
end_total_time = time.time()
logging.info(f"\n--- TỔNG THỜI GIAN CHẠY: {end_total_time - start_total_time:.2f} giây ---")

if generated_maps_filepath and generated_plan_filepath:
    print("\n✅✅✅ HOÀN THÀNH TẤT CẢ CÁC BƯỚC! ✅✅✅")
    print(f"File địa điểm (Maps): {generated_maps_filepath}")
    print(f"File kế hoạch (Gemini): {generated_plan_filepath}")
elif generated_maps_filepath:
    print("\n⚠️  HOÀN THÀNH MỘT PHẦN ⚠️")
    print("Chỉ tìm được địa điểm nhưng không tạo được kế hoạch.")
    print(f"File địa điểm (Maps): {generated_maps_filepath}")
else:
    print("\n❌❌❌ THẤT BẠI ❌❌❌")
    print("Không thể hoàn thành bất kỳ bước nào.")