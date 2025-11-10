# # Đây là file main_runner.py
# # Đảm bảo file này nằm CÙNG THƯ MỤC với:
# # - api_fetcher.py
# # - gemini_planner.py
# # - file .env của bạn

# import api_fetcher
# import gemini_planner  # <-- Import file mới
# import time
# import logging

# # --- Cấu hình logging ---
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# logging.info("--- BẮT ĐẦU CHƯƠG TRÌNH CHÍNH (main_runner.py) ---")

# # --- 1. CẤU HÌNH ĐẦU VÀO CỦA BẠN ---

# # Định nghĩa vị trí dưới dạng dictionary (để dùng cho Gemini)
# NEW_USER_LOCATION_DICT = {"lat": 21.0278, "lng": 105.8342}

# # Tự động tạo chuỗi string (để dùng cho Google Maps API)
# NEW_USER_LOCATION_STRING = f"{NEW_USER_LOCATION_DICT['lat']},{NEW_USER_LOCATION_DICT['lng']}"

# NEW_USER_RADIUS = 5000                      # Bán kính 10km
# USER_PREFERENCES = ['pref_cafe', 'pref_sento', 'pref_bookstore']

# # Biến thời gian MỚI mà bạn yêu cầu
# NEW_TRIP_DURATION = "khoảng 4-5 tiếng, bao gồm 1 bữa ăn trưa và 1 buổi cafe chiều"

# # --- 2. GỌI API GOOGLE MAPS (PHASE 1) ---

# logging.info(f"Đang chuẩn bị tìm kiếm địa điểm cho: {USER_PREFERENCES}")
# logging.info(f"Vị trí: {NEW_USER_LOCATION_STRING}, Bán kính: {NEW_USER_RADIUS}m")

# start_total_time = time.time()
# generated_maps_filepath = None
# generated_plan_filepath = None

# try:
#     # Gọi hàm từ api_fetcher
#     generated_maps_filepath = api_fetcher.run_search_and_save(
#         USER_PREFERENCES,
#         NEW_USER_LOCATION_STRING,
#         NEW_USER_RADIUS
#     )

#     if generated_maps_filepath:
#         logging.info(f"✅ Đã tìm và lưu địa điểm vào: {generated_maps_filepath}")
        
#         # --- 3. GỌI API GEMINI (PHASE 2) ---
#         # Chỉ chạy nếu Phase 1 thành công
        
#         logging.info(f"\n--- Bắt đầu tạo kế hoạch với Gemini ---")
#         logging.info(f"Input file: {generated_maps_filepath}")
#         logging.info(f"Vị trí: {NEW_USER_LOCATION_DICT}")
#         logging.info(f"Thời gian: {NEW_TRIP_DURATION}")
        
#         # Gọi hàm từ gemini_planner
#         generated_plan_filepath = gemini_planner.create_trip_plan_from_file(
#             places_input_filepath=generated_maps_filepath,
#             user_location_dict=NEW_USER_LOCATION_DICT,
#             requested_duration_text=NEW_TRIP_DURATION
#         )
        
#         if generated_plan_filepath:
#             logging.info(f"✅ Đã tạo và lưu kế hoạch vào: {generated_plan_filepath}")
#         else:
#             logging.error("❌ Lỗi khi tạo kế hoạch với Gemini.")

#     else:
#         logging.error("❌ KHÔNG THÀNH CÔNG (Google Maps API).")
#         logging.warning("Không tìm thấy địa điểm, sẽ không chạy Gemini.")

# except Exception as e:
#     logging.critical(f"\n🔥🔥🔥 ĐÃ XẢY RA LỖI NGHIÊM TRỌNG TRONG main_runner: {e}", exc_info=True)


# # --- 4. TỔNG KẾT ---
# end_total_time = time.time()
# logging.info(f"\n--- TỔNG THỜI GIAN CHẠY: {end_total_time - start_total_time:.2f} giây ---")

# if generated_maps_filepath and generated_plan_filepath:
#     print("\n✅✅✅ HOÀN THÀNH TẤT CẢ CÁC BƯỚC! ✅✅✅")
#     print(f"File địa điểm (Maps): {generated_maps_filepath}")
#     print(f"File kế hoạch (Gemini): {generated_plan_filepath}")
# elif generated_maps_filepath:
#     print("\n⚠️  HOÀN THÀNH MỘT PHẦN ⚠️")
#     print("Chỉ tìm được địa điểm nhưng không tạo được kế hoạch.")
#     print(f"File địa điểm (Maps): {generated_maps_filepath}")
# else:
#     print("\n❌❌❌ THẤT BẠI ❌❌❌")
#     print("Không thể hoàn thành bất kỳ bước nào.")
import api_fetcher
import gemini_planner
import time
import logging
import os
import uuid
import threading
from flask import Flask, request, jsonify, make_response, redirect, url_for, send_from_directory
from flask_cors import CORS
from pathlib import Path

# --- 1. CẤU HÌNH LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 2. ĐỊNH NGHĨA ĐƯỜNG DẪN GỐC ---
# Giả sử file này (main_runner.py) nằm trong /API
# Và các file JSON, Front nằm ở thư mục cha
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
JSON_DIR = os.path.join(PROJECT_ROOT, 'json')
FRONT_DIR = os.path.join(PROJECT_ROOT, 'Front')

logging.info(f"Project Root: {PROJECT_ROOT}")
logging.info(f"JSON Dir: {JSON_DIR}")
logging.info(f"Front Dir: {FRONT_DIR}")

# --- 3. KHỞI TẠO FLASK SERVER ---
app = Flask(__name__)
CORS(app)  # Vẫn giữ CORS, dù không cần thiết khi cùng 1 nguồn
logging.info("--- KHỞI TẠO FLASK SERVER VÀ CẤU HÌNH CORS ---")

# --- 4. TẠO BỘ NHỚ ĐỂ LƯU TRỮ CÁC JOB ---
jobs = {}

# --- 5. HÀM TÁC VỤ NẶNG (SẼ CHẠY TRONG NỀN) ---
def run_the_whole_job(job_id, data):
    """
    Đây là hàm chạy 80 giây (Maps + Gemini).
    Nó chạy trong một luồng (thread) riêng để không làm treo server.
    """
    try:
        logging.info(f"[JOB: {job_id}] --- Bắt đầu tác vụ chạy nền ---")
        
        # Lấy dữ liệu từ data
        NEW_USER_LOCATION_DICT = data['location']
        USER_PREFERENCES = data['preferences']
        NEW_TRIP_DURATION = data['duration']
        NEW_USER_RADIUS = 5000  
        NEW_USER_LOCATION_STRING = f"{NEW_USER_LOCATION_DICT['lat']},{NEW_USER_LOCATION_DICT['lng']}"

        # --- Chạy Google Maps (Phase 1) ---
        logging.info(f"[JOB: {job_id}] Đang gọi Google Maps API...")
        generated_maps_filepath = api_fetcher.run_search_and_save(
            USER_PREFERENCES,
            NEW_USER_LOCATION_STRING,
            NEW_USER_RADIUS
        )
        if not generated_maps_filepath:
            raise Exception("Không tìm thấy địa điểm (Google Maps API).")

        logging.info(f"[JOB: {job_id}] ✅ Maps OK: {generated_maps_filepath}")

        # --- Chạy Gemini (Phase 2) ---
        logging.info(f"[JOB: {job_id}] Đang gọi Gemini API...")
        generated_plan_filepath = gemini_planner.create_trip_plan_from_file(
            places_input_filepath=generated_maps_filepath,
            user_location_dict=NEW_USER_LOCATION_DICT,
            requested_duration_text=NEW_TRIP_DURATION
        )
        if not generated_plan_filepath:
            raise Exception("Lỗi khi tạo kế hoạch với Gemini.")

        logging.info(f"[JOB: {job_id}] ✅ Gemini OK: {generated_plan_filepath}")

        # --- Xử lý đường dẫn file (SỬA LỖI) ---
        # Tạo đường dẫn URL mà trình duyệt có thể gọi
        plan_filename = Path(generated_plan_filepath).name
        map_filename = Path(generated_maps_filepath).name
        
        plan_file_url = f"/json/GeminiAPIResponse/{plan_filename}" # Đây là URL
        map_file_url = f"/json/GoogleMapAPIResponse/{map_filename}" # Đây là URL

        # --- CẬP NHẬT JOB: THÀNH CÔNG ---
        logging.info(f"[JOB: {job_id}] --- Tác vụ chạy nền HOÀN THÀNH ---")
        jobs[job_id] = {
            "status": "complete",
            "planFile": plan_file_url, # Trả về URL
            "mapFile": map_file_url   # Trả về URL
        }

    except Exception as e:
        # --- CẬP NHẬT JOB: THẤT BẠI ---
        logging.error(f"[JOB: {job_id}] --- Tác vụ chạy nền THẤT BẠI: {e} ---", exc_info=True)
        jobs[job_id] = {
            "status": "error",
            "error": str(e)
        }


# --- 6. TẠO API ROUTES ---

# === ROUTE 1: BẮT ĐẦU JOB ===
@app.route('/api/start-job', methods=['POST', 'OPTIONS']) 
def handle_start_job():
    """
    Nhận yêu cầu, tạo job_id, khởi động luồng chạy nền,
    và trả về job_id NGAY LẬP TỨC.
    """
    if request.method == 'OPTIONS':
        # Xử lý preflight thủ công (dù CORS(app) nên làm)
        response = make_response(jsonify({"message": "CORS preflight OK"}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    data = request.json
    if not data:
        logging.error("Không nhận được dữ liệu JSON")
        return jsonify({"success": False, "error": "No data received"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running"}
    logging.info(f"[JOB: {job_id}] Đã nhận yêu cầu. Bắt đầu luồng chạy nền...")

    thread = threading.Thread(target=run_the_whole_job, args=(job_id, data))
    thread.start() 

    return jsonify({
        "success": True,
        "job_id": job_id
    }), 202 # 202 = Accepted (Đã chấp nhận)

# === ROUTE 2: KIỂM TRA JOB ===
@app.route('/api/check-status', methods=['GET']) # Chỉ cần GET
def handle_check_status():
    """
    Frontend sẽ gọi đường dẫn này 5 giây/lần để "hỏi thăm".
    """
    job_id = request.args.get('job_id')
    if not job_id:
        return jsonify({"success": False, "error": "Thiếu job_id"}), 400

    logging.info(f"[JOB: {job_id}] Frontend đang 'hỏi thăm' trạng thái...")
    
    job = jobs.get(job_id)
    
    if not job:
        return jsonify({"success": False, "error": "Không tìm thấy Job ID"}), 404
        
    return jsonify({"success": True, "data": job}), 200


# --- 7. TẠO ROUTE ĐỂ PHỤC VỤ (SERVE) FILE ---

# === ROUTE 3: PHỤC VỤ TRANG CHỦ (Input) ===
@app.route('/')
def serve_index():
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/main.html")
    # Đảm bảo tên file của bạn là 'minitrip_input.html' và nằm trong 'Front'
    return send_from_directory(FRONT_DIR, 'main.html') 

# === ROUTE 4: PHỤC VỤ TRANG KẾT QUẢ (Map) ===
@app.route('/map')
def serve_map():
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/map.html")
    # Đảm bảo file của bạn là 'map.html' và nằm trong 'Front'
    return send_from_directory(FRONT_DIR, 'map.html')

# === ROUTE 5: PHỤC VỤ FILE JSON (Kết quả) ===
@app.route('/json/GeminiAPIResponse/<path:filename>')
def serve_gemini_json(filename):
    logging.info(f"Đang phục vụ file Gemini JSON: {filename}")
    directory = os.path.join(JSON_DIR, 'GeminiAPIResponse')
    return send_from_directory(directory, filename)

@app.route('/json/GoogleMapAPIResponse/<path:filename>')
def serve_maps_json(filename):
    logging.info(f"Đang phục vụ file Maps JSON: {filename}")
    directory = os.path.join(JSON_DIR, 'GoogleMapAPIResponse')
    return send_from_directory(directory, filename)


# --- 8. CHẠY SERVER ---
if __name__ == '__main__':
    logging.info(f"--- BẮT ĐẦU CHẠY SERVER (All-in-One) tại http://127.0.0.1:5000 ---")
    # Đã tắt reloader để tránh lỗi
    app.run(debug=True, port=5000, use_reloader=False)