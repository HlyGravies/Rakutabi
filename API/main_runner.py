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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
JSON_DIR = os.path.join(PROJECT_ROOT, 'json')
FRONT_DIR = os.path.join(PROJECT_ROOT, 'Front')

logging.info(f"Project Root: {PROJECT_ROOT}")
logging.info(f"JSON Dir: {JSON_DIR}")
logging.info(f"Front Dir: {FRONT_DIR}")

# --- 3. KHỞI TẠO FLASK SERVER ---
app = Flask(__name__)
CORS(app)  
logging.info("--- KHỞI TẠO FLASK SERVER VÀ CẤU HÌNH CORS ---")

# --- 4. TẠO BỘ NHỚ ĐỂ LƯU TRỮ CÁC JOB ---
jobs = {}

# --- 5. HÀM TÁC VỤ NẶNG (SẼ CHẠY TRONG NỀN) ---
# (Hàm run_the_whole_job giữ nguyên, không thay đổi)
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

# === ROUTE 1A: BẮT ĐẦU JOB (TỪ main.html) ===
@app.route('/api/start-job', methods=['POST', 'OPTIONS']) 
def handle_start_job():
    if request.method == 'OPTIONS':
        response = make_response(jsonify({"message": "CORS preflight OK"}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "No data received"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running"}
    logging.info(f"[JOB: {job_id}] Đã nhận yêu cầu. Bắt đầu luồng chạy nền...")

    thread = threading.Thread(target=run_the_whole_job, args=(job_id, data))
    thread.start() 

    return jsonify({
        "success": True,
        "job_id": job_id
    }), 202

# === ROUTE 1B: KIỂM TRA JOB ===
@app.route('/api/check-status', methods=['GET']) 
def handle_check_status():
    job_id = request.args.get('job_id')
    if not job_id:
        return jsonify({"success": False, "error": "Thiếu job_id"}), 400

    logging.info(f"[JOB: {job_id}] Frontend đang 'hỏi thăm' trạng thái...")
    job = jobs.get(job_id)
    
    if not job:
        return jsonify({"success": False, "error": "Không tìm thấy Job ID"}), 404
        
    return jsonify({"success": True, "data": job}), 200

# === ROUTE 2A: API ĐĂNG KÝ (TỪ register.html) ===
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def handle_register():
    if request.method == 'OPTIONS':
        response = make_response(jsonify({"message": "CORS preflight OK"}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
        
    data = request.json
    logging.info(f"--- NHẬN ĐƯỢC YÊU CẦU ĐĂNG KÝ: {data.get('email')} ---")
    # (Đây là nơi bạn code logic đăng ký, lưu vào database...)
    # Giả lập thành công:
    return jsonify({"success": True, "message": "Đăng ký thành công!"}), 200

# === ROUTE 2B: API ĐĂNG NHẬP (TỪ login.html) ===
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def handle_login():
    if request.method == 'OPTIONS':
        response = make_response(jsonify({"message": "CORS preflight OK"}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    data = request.json
    logging.info(f"--- NHẬN ĐƯỢC YÊU CẦU ĐĂNG NHẬP: {data.get('email')} ---")
    # (Đây là nơi bạn code logic check database...)
    # Giả lập thành công:
    return jsonify({"success": True, "message": "Đăng nhập thành công!", "token": "dummy_token_12345"}), 200


# --- 7. TẠO ROUTE ĐỂ PHỤC VỤ (SERVE) FILE HTML ---

# === ROUTE 3: PHỤC VỤ TRANG CHỦ (Input) ===
@app.route('/')
def serve_index():
    # *** ĐÃ SỬA TÊN FILE Ở ĐÂY ***
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/minitrip_input.html")
    # Đảm bảo tên file của bạn là 'minitrip_input.html' và nằm trong 'Front'
    return send_from_directory(FRONT_DIR, 'minitrip_input.html') 

# === ROUTE 4: PHỤC VỤ TRANG KẾT QUẢ (Map) ===
@app.route('/map')
def serve_map():
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/map.html")
    return send_from_directory(FRONT_DIR, 'map.html')

# === ROUTE 5: PHỤC VỤ TRANG ĐĂNG NHẬP (MỚI) ===
@app.route('/login')
def serve_login():
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/login.html")
    return send_from_directory(FRONT_DIR, 'login.html')

# === ROUTE 6: PHỤC VỤ TRANG ĐĂNG KÝ (MỚI) ===
@app.route('/register')
def serve_register():
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/register.html")
    return send_from_directory(FRONT_DIR, 'register.html')

# === ROUTE 7: PHỤC VỤ FILE JSON (Kết quả) ===
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
    app.run(debug=True, port=5000, use_reloader=False)