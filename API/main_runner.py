import api_fetcher
import gemini_planner
import time
import logging
import os
import uuid       
import threading  
import sqlite3 
from werkzeug.security import generate_password_hash, check_password_hash 
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
DB_PATH = os.path.join(BASE_DIR, 'rakutabi.db') 

logging.info(f"Project Root: {PROJECT_ROOT}")
logging.info(f"JSON Dir: {JSON_DIR}")
logging.info(f"Front Dir: {FRONT_DIR}")
logging.info(f"Database Path: {DB_PATH}")

# --- 3. KHỞI TẠO DATABASE (MỚI) ---
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Tạo bảng 'users' nếu nó chưa tồn tại
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        conn.commit()
        conn.close()
        logging.info("Database đã được khởi tạo/kiểm tra thành công.")
    except Exception as e:
        logging.error(f"LỖI khi khởi tạo database: {e}")

# --- 4. KHỞI TẠO FLASK SERVER ---
app = Flask(__name__)
CORS(app)  
logging.info("--- KHỞI TẠO FLASK SERVER VÀ CẤU HÌNH CORS ---")

# --- 5. TẠO BỘ NHỚ ĐỂ LƯU TRỮ CÁC JOB ---
jobs = {}

# --- 6. HÀM TÁC VỤ NẶNG (SẼ CHẠY TRONG NỀN) ---
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


# --- 7. TẠO API ROUTES ---

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

# === ROUTE 2A: API ĐĂNG KÝ ===
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def handle_register():
    if request.method == 'OPTIONS':
        response = make_response(jsonify({"message": "CORS preflight OK"}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
        
    data = request.json
    nickname = data.get('nickname')
    email = data.get('email')
    password = data.get('password')

    if not nickname or not email or not password:
        return jsonify({"success": False, "message": "Thiếu thông tin."}), 400
    
    password_hash = generate_password_hash(password)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (nickname, email, password_hash) VALUES (?, ?, ?)", 
                       (nickname, email, password_hash))
        conn.commit()
        conn.close()
        
        logging.info(f"--- ĐĂNG KÝ THÀNH CÔNG: {email} ---")
        return jsonify({"success": True, "message": "Đăng ký thành công!"}), 200

    except sqlite3.IntegrityError:
        conn.close()
        logging.warning(f"--- ĐĂNG KÝ THẤT BẠI (Email đã tồn tại): {email} ---")
        return jsonify({"success": False, "message": "Email này đã được sử dụng."}), 409
    except Exception as e:
        conn.close()
        logging.error(f"--- LỖI ĐĂNG KÝ: {e} ---")
        return jsonify({"success": False, "message": "Lỗi server."}), 500

# === ROUTE 2B: API ĐĂNG NHẬP ===
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def handle_login():
    if request.method == 'OPTIONS':
        response = make_response(jsonify({"message": "CORS preflight OK"}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Thiếu email hoặc mật khẩu."}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user is None:
            logging.warning(f"--- ĐĂNG NHẬP THẤT BẠI (Không tìm thấy user): {email} ---")
            return jsonify({"success": False, "message": "Sai email hoặc mật khẩu."}), 401
        
        if check_password_hash(user['password_hash'], password):
            logging.info(f"--- ĐĂNG NHẬP THÀNH CÔNG: {email} ---")
            
            response = make_response(jsonify({
                "success": True, 
                "message": "Đăng nhập thành công!", 
                "nickname": user['nickname']
            }))
            response.set_cookie('user_nickname', user['nickname'], max_age=3600*24) 
            return response, 200
        else:
            logging.warning(f"--- ĐĂNG NHẬP THẤT BẠI (Sai mật khẩu): {email} ---")
            return jsonify({"success": False, "message": "Sai email hoặc mật khẩu."}), 401

    except Exception as e:
        conn.close()
        logging.error(f"--- LỖI ĐĂNG NHẬP: {e} ---")
        return jsonify({"success": False, "message": "Lỗi server."}), 500

# === ROUTE 2C: API ĐĂNG XUẤT ===
@app.route('/api/logout', methods=['POST', 'OPTIONS'])
def handle_logout():
    if request.method == 'OPTIONS':
        response = make_response(jsonify({"message": "CORS preflight OK"}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
        
    logging.info("--- ĐÃ NHẬN YÊU CẦU ĐĂNG XUẤT ---")
    response = make_response(jsonify({"success": True, "message": "Đã đăng xuất"}))
    response.delete_cookie('user_nickname')
    return response, 200

# === ROUTE 2D: API LẤY THÔNG TIN USER ===
@app.route('/api/profile', methods=['GET'])
def handle_get_profile():
    user_nickname = request.cookies.get('user_nickname')
    
    if not user_nickname:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
    
    try:
        # Lấy thêm email từ DB
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT nickname, email FROM users WHERE nickname = ?", (user_nickname,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return jsonify({"success": True, "nickname": user['nickname'], "email": user['email']})
        else:
            return jsonify({"success": False, "message": "Không tìm thấy user"}), 404
            
    except Exception as e:
        logging.error(f"--- LỖI LẤY PROFILE: {e} ---")
        return jsonify({"success": False, "message": "Lỗi server."}), 500

# === ROUTE 2E: API CẬP NHẬT PROFILE ===
@app.route('/api/profile/update', methods=['POST', 'OPTIONS'])
def handle_update_profile():
    if request.method == 'OPTIONS':
        response = make_response(jsonify({"message": "CORS preflight OK"}))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    current_nickname = request.cookies.get('user_nickname')
    if not current_nickname:
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.json
    new_nickname = data.get('nickname')
    new_password = data.get('password') 

    if not new_nickname:
        return jsonify({"success": False, "message": "Nickname không được để trống."}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if new_password:
            logging.info(f"--- CẬP NHẬT PROFILE (CÓ MẬT KHẨU) CHO: {current_nickname} ---")
            new_password_hash = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET nickname = ?, password_hash = ? WHERE nickname = ?",
                           (new_nickname, new_password_hash, current_nickname))
        else:
            logging.info(f"--- CẬP NHẬT PROFILE (CHỈ NICKNAME) CHO: {current_nickname} ---")
            cursor.execute("UPDATE users SET nickname = ? WHERE nickname = ?",
                           (new_nickname, current_nickname))
        
        conn.commit()
        conn.close()
        
        response = make_response(jsonify({"success": True, "message": "Cập nhật thành công!"}))
        response.set_cookie('user_nickname', new_nickname, max_age=3600*24)
        
        return response, 200

    except sqlite3.IntegrityError:
        conn.close()
        logging.warning(f"--- CẬP NHẬT THẤT BẠI (Nickname đã tồn tại): {new_nickname} ---")
        return jsonify({"success": False, "message": "Nickname này đã được sử dụng."}), 409
    except Exception as e:
        conn.close()
        logging.error(f"--- LỖI CẬP NHẬT PROFILE: {e} ---")
        return jsonify({"success": False, "message": "Lỗi server."}), 500


# --- 8. TẠO ROUTE ĐỂ PHỤC VỤ (SERVE) FILE HTML ---

# === ROUTE 3: PHỤC VỤ TRANG CHỦ (Input) ===
@app.route('/')
def serve_index():
    user_nickname = request.cookies.get('user_nickname')
    if not user_nickname:
        logging.warning("--- Chưa đăng nhập, chuyển hướng về /login ---")
        return redirect(url_for('serve_login'))
        
    logging.info(f"Đã đăng nhập (User: {user_nickname}). Đang phục vụ file: {FRONT_DIR}/main.html")
    # Đảm bảo file của bạn tên là 'main.html'
    return send_from_directory(FRONT_DIR, 'main.html') 

# === ROUTE 4: PHỤC VỤ TRANG KẾT QUẢ (Map) ===
@app.route('/map')
def serve_map():
    user_nickname = request.cookies.get('user_nickname')
    if not user_nickname:
        logging.warning("--- Chưa đăng nhập, chuyển hướng về /login ---")
        return redirect(url_for('serve_login'))
        
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/map.html")
    return send_from_directory(FRONT_DIR, 'map.html')

# === ROUTE 5: PHỤC VỤ TRANG ĐĂNG NHẬP ===
@app.route('/login')
def serve_login():
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/login.html")
    return send_from_directory(FRONT_DIR, 'login.html')

# === ROUTE 6: PHỤC VỤ TRANG ĐĂNG KÝ ===
@app.route('/register')
def serve_register():
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/register.html")
    return send_from_directory(FRONT_DIR, 'register.html')
    
# === ROUTE 7: PHỤC VỤ TRANG HỒ SƠ ===
@app.route('/profile')
def serve_profile():
    user_nickname = request.cookies.get('user_nickname')
    if not user_nickname:
        logging.warning("--- Chưa đăng nhập, chuyển hướng về /login ---")
        return redirect(url_for('serve_login'))
        
    logging.info(f"Đang phục vụ file: {FRONT_DIR}/profile.html")
    return send_from_directory(FRONT_DIR, 'profile.html') 

# === ROUTE 8: PHỤC VỤ FILE JSON (Kết quả) ===
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


# --- 9. CHẠY SERVER ---
if __name__ == '__main__':
    init_db() 
    logging.info(f"--- BẮT ĐẦU CHẠY SERVER (All-in-One) tại http://127.0.0.1:5000 ---")
    app.run(debug=True, port=5000, use_reloader=False)