# import api_fetcher
# import gemini_planner
# import time
# import logging
# import os
# import uuid       
# import threading  
# import sqlite3 
# from werkzeug.security import generate_password_hash, check_password_hash 
# from flask import Flask, request, jsonify, make_response, redirect, url_for, send_from_directory
# from flask_cors import CORS
# from pathlib import Path

# # --- 1. CẤU HÌNH LOGGING ---
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# # --- 2. ĐỊNH NGHĨA ĐƯỜNG DẪN GỐC ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))
# JSON_DIR = os.path.join(PROJECT_ROOT, 'json')
# FRONT_DIR = os.path.join(PROJECT_ROOT, 'Front')
# DB_PATH = os.path.join(BASE_DIR, 'rakutabi.db') 

# logging.info(f"Project Root: {PROJECT_ROOT}")
# logging.info(f"JSON Dir: {JSON_DIR}")
# logging.info(f"Front Dir: {FRONT_DIR}")
# logging.info(f"Database Path: {DB_PATH}")

# # --- 3. KHỞI TẠO DATABASE ---
# def init_db():
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         cursor = conn.cursor()
        
#         # Bảng users
#         cursor.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             nickname TEXT NOT NULL,
#             email TEXT NOT NULL UNIQUE,
#             password_hash TEXT NOT NULL,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         );
#         ''')

#         # Bảng favorites (Lưu lộ trình yêu thích)
#         cursor.execute('''
#         CREATE TABLE IF NOT EXISTS favorites (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER NOT NULL,
#             file_path TEXT NOT NULL,
#             plan_title TEXT NOT NULL,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (user_id) REFERENCES users (id),
#             UNIQUE(user_id, file_path, plan_title) 
#         );
#         ''')

#         conn.commit()
#         conn.close()
#         logging.info("Database (users & favorites) đã được khởi tạo thành công.")
#     except Exception as e:
#         logging.error(f"LỖI khi khởi tạo database: {e}")

# # --- 4. KHỞI TẠO FLASK SERVER ---
# app = Flask(__name__)
# CORS(app)  
# logging.info("--- KHỞI TẠO FLASK SERVER VÀ CẤU HÌNH CORS ---")

# # --- 5. BỘ NHỚ JOB ---
# jobs = {}

# # --- 6. HÀM TÁC VỤ NỀN (CHẠY MAPS & GEMINI) ---
# def run_the_whole_job(job_id, data):
#     try:
#         logging.info(f"[JOB: {job_id}] --- Bắt đầu tác vụ chạy nền ---")
        
#         NEW_USER_LOCATION_DICT = data['location']
#         USER_PREFERENCES = data['preferences']
#         NEW_TRIP_DURATION = data['duration']
#         NEW_USER_RADIUS = 5000  
#         NEW_USER_LOCATION_STRING = f"{NEW_USER_LOCATION_DICT['lat']},{NEW_USER_LOCATION_DICT['lng']}"

#         # Phase 1: Maps
#         logging.info(f"[JOB: {job_id}] Đang gọi Google Maps API...")
#         generated_maps_filepath = api_fetcher.run_search_and_save(
#             USER_PREFERENCES,
#             NEW_USER_LOCATION_STRING,
#             NEW_USER_RADIUS
#         )
#         if not generated_maps_filepath:
#             raise Exception("Không tìm thấy địa điểm (Google Maps API).")

#         logging.info(f"[JOB: {job_id}] ✅ Maps OK: {generated_maps_filepath}")

#         # Phase 2: Gemini
#         logging.info(f"[JOB: {job_id}] Đang gọi Gemini API...")
#         generated_plan_filepath = gemini_planner.create_trip_plan_from_file(
#             places_input_filepath=generated_maps_filepath,
#             user_location_dict=NEW_USER_LOCATION_DICT,
#             requested_duration_text=NEW_TRIP_DURATION
#         )
#         if not generated_plan_filepath:
#             raise Exception("Lỗi khi tạo kế hoạch với Gemini.")

#         logging.info(f"[JOB: {job_id}] ✅ Gemini OK: {generated_plan_filepath}")

#         # Tạo URL trả về
#         plan_filename = Path(generated_plan_filepath).name
#         map_filename = Path(generated_maps_filepath).name
        
#         plan_file_url = f"/json/GeminiAPIResponse/{plan_filename}"
#         map_file_url = f"/json/GoogleMapAPIResponse/{map_filename}"

#         jobs[job_id] = {
#             "status": "complete",
#             "planFile": plan_file_url,
#             "mapFile": map_file_url
#         }
#         logging.info(f"[JOB: {job_id}] --- HOÀN THÀNH ---")

#     except Exception as e:
#         logging.error(f"[JOB: {job_id}] --- THẤT BẠI: {e} ---", exc_info=True)
#         jobs[job_id] = {
#             "status": "error",
#             "error": str(e)
#         }

# # --- 7. API ROUTES ---

# # === JOB ROUTES ===
# @app.route('/api/start-job', methods=['POST', 'OPTIONS']) 
# def handle_start_job():
#     if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)
    
#     data = request.json
#     if not data: return jsonify({"success": False, "error": "No data"}), 400

#     job_id = str(uuid.uuid4())
#     jobs[job_id] = {"status": "running"}
    
#     thread = threading.Thread(target=run_the_whole_job, args=(job_id, data))
#     thread.start() 

#     return jsonify({"success": True, "job_id": job_id}), 202

# @app.route('/api/check-status', methods=['GET']) 
# def handle_check_status():
#     job_id = request.args.get('job_id')
#     job = jobs.get(job_id)
#     if not job: return jsonify({"success": False, "error": "Không tìm thấy Job ID"}), 404
#     return jsonify({"success": True, "data": job}), 200

# # === AUTH ROUTES ===
# @app.route('/api/register', methods=['POST', 'OPTIONS'])
# def handle_register():
#     if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)
        
#     data = request.json
#     nickname, email, password = data.get('nickname'), data.get('email'), data.get('password')

#     if not nickname or not email or not password:
#         return jsonify({"success": False, "message": "Thiếu thông tin."}), 400
    
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         cursor = conn.cursor()
#         cursor.execute("INSERT INTO users (nickname, email, password_hash) VALUES (?, ?, ?)", 
#                        (nickname, email, generate_password_hash(password)))
#         conn.commit()
#         conn.close()
#         return jsonify({"success": True, "message": "Đăng ký thành công!"}), 200
#     except sqlite3.IntegrityError:
#         return jsonify({"success": False, "message": "Email đã tồn tại."}), 409
#     except Exception:
#         return jsonify({"success": False, "message": "Lỗi server."}), 500

# @app.route('/api/login', methods=['POST', 'OPTIONS'])
# def handle_login():
#     if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)

#     data = request.json
#     email, password = data.get('email'), data.get('password')
    
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         conn.row_factory = sqlite3.Row 
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
#         user = cursor.fetchone()
#         conn.close()
        
#         if user and check_password_hash(user['password_hash'], password):
#             response = make_response(jsonify({"success": True, "message": "Đăng nhập thành công!", "nickname": user['nickname']}))
#             response.set_cookie('user_nickname', user['nickname'], max_age=3600*24) 
#             return response, 200
#         else:
#             return jsonify({"success": False, "message": "Sai email hoặc mật khẩu."}), 401
#     except Exception:
#         return jsonify({"success": False, "message": "Lỗi server."}), 500

# @app.route('/api/logout', methods=['POST', 'OPTIONS'])
# def handle_logout():
#     if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)
#     response = make_response(jsonify({"success": True, "message": "Đã đăng xuất"}))
#     response.delete_cookie('user_nickname')
#     return response, 200

# @app.route('/api/profile', methods=['GET'])
# def handle_get_profile():
#     user_nickname = request.cookies.get('user_nickname')
#     if not user_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
    
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         conn.row_factory = sqlite3.Row
#         cursor = conn.cursor()
#         cursor.execute("SELECT nickname, email FROM users WHERE nickname = ?", (user_nickname,))
#         user = cursor.fetchone()
#         conn.close()
        
#         if user: return jsonify({"success": True, "nickname": user['nickname'], "email": user['email']})
#         else: return jsonify({"success": False, "message": "Không tìm thấy user"}), 404
#     except Exception:
#         return jsonify({"success": False, "message": "Lỗi server."}), 500

# @app.route('/api/profile/update', methods=['POST', 'OPTIONS'])
# def handle_update_profile():
#     if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)

#     current_nickname = request.cookies.get('user_nickname')
#     if not current_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
#     data = request.json
#     new_nickname = data.get('nickname')
#     new_password = data.get('password') 

#     try:
#         conn = sqlite3.connect(DB_PATH)
#         cursor = conn.cursor()
        
#         if new_password:
#             cursor.execute("UPDATE users SET nickname = ?, password_hash = ? WHERE nickname = ?",
#                            (new_nickname, generate_password_hash(new_password), current_nickname))
#         else:
#             cursor.execute("UPDATE users SET nickname = ? WHERE nickname = ?",
#                            (new_nickname, current_nickname))
#         conn.commit()
#         conn.close()
        
#         response = make_response(jsonify({"success": True, "message": "Cập nhật thành công!"}))
#         response.set_cookie('user_nickname', new_nickname, max_age=3600*24)
#         return response, 200
#     except sqlite3.IntegrityError:
#         return jsonify({"success": False, "message": "Nickname đã tồn tại."}), 409
#     except Exception:
#         return jsonify({"success": False, "message": "Lỗi server."}), 500

# # === FAVORITES ROUTES (ĐẦY ĐỦ: ADD, GET, DELETE) ===

# # 1. THÊM YÊU THÍCH
# @app.route('/api/favorites/add', methods=['POST', 'OPTIONS'])
# def handle_add_favorite():
#     if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)

#     user_nickname = request.cookies.get('user_nickname')
#     if not user_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401

#     data = request.json
#     raw_path = data.get('file_path') 
#     plan_title = data.get('plan_title')

#     if not raw_path or not plan_title:
#         return jsonify({"success": False, "message": "Thiếu thông tin"}), 400
    
#     # Chỉ lấy tên file (bỏ đường dẫn) để lưu DB cho gọn
#     filename = os.path.basename(raw_path)

#     try:
#         conn = sqlite3.connect(DB_PATH)
#         conn.row_factory = sqlite3.Row
#         cursor = conn.cursor()
        
#         cursor.execute("SELECT id FROM users WHERE nickname = ?", (user_nickname,))
#         user = cursor.fetchone()
        
#         if user:
#             cursor.execute("INSERT OR IGNORE INTO favorites (user_id, file_path, plan_title) VALUES (?, ?, ?)", 
#                            (user['id'], filename, plan_title))
#             conn.commit()
#             conn.close()
#             return jsonify({"success": True, "message": "Đã lưu vào mục yêu thích!"}), 200
#         else:
#             return jsonify({"success": False, "message": "User không tồn tại"}), 404
#     except Exception as e:
#         logging.error(f"Lỗi lưu fav: {e}")
#         return jsonify({"success": False, "message": str(e)}), 500

# # 2. LẤY DANH SÁCH YÊU THÍCH
# @app.route('/api/favorites', methods=['GET'])
# def handle_get_favorites():
#     user_nickname = request.cookies.get('user_nickname')
#     if not user_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401

#     try:
#         conn = sqlite3.connect(DB_PATH)
#         conn.row_factory = sqlite3.Row
#         cursor = conn.cursor()
#         cursor.execute("""
#             SELECT f.id, f.file_path, f.plan_title, f.created_at 
#             FROM favorites f
#             JOIN users u ON f.user_id = u.id
#             WHERE u.nickname = ?
#             ORDER BY f.created_at DESC
#         """, (user_nickname,))
        
#         rows = cursor.fetchall()
#         favorites = [dict(row) for row in rows]
#         conn.close()
#         return jsonify({"success": True, "favorites": favorites}), 200
#     except Exception as e:
#         logging.error(f"Lỗi lấy fav: {e}")
#         return jsonify({"success": False, "message": "Lỗi server"}), 500

# # 3. XÓA YÊU THÍCH (MỚI THÊM)
# @app.route('/api/favorites/delete', methods=['POST', 'OPTIONS'])
# def handle_delete_favorite():
#     if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)

#     user_nickname = request.cookies.get('user_nickname')
#     if not user_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401

#     data = request.json
#     raw_path = data.get('file_path') 
#     plan_title = data.get('plan_title')

#     if not raw_path or not plan_title:
#         return jsonify({"success": False, "message": "Thiếu thông tin"}), 400
    
#     filename = os.path.basename(raw_path)

#     try:
#         conn = sqlite3.connect(DB_PATH)
#         conn.row_factory = sqlite3.Row
#         cursor = conn.cursor()
        
#         cursor.execute("SELECT id FROM users WHERE nickname = ?", (user_nickname,))
#         user = cursor.fetchone()
        
#         if user:
#             cursor.execute("""
#                 DELETE FROM favorites 
#                 WHERE user_id = ? AND file_path = ? AND plan_title = ?
#             """, (user['id'], filename, plan_title))
            
#             conn.commit()
#             conn.close()
#             return jsonify({"success": True, "message": "Đã xóa khỏi mục yêu thích"}), 200
#         else:
#             return jsonify({"success": False, "message": "User không tồn tại"}), 404
#     except Exception as e:
#         logging.error(f"Lỗi xóa fav: {e}")
#         return jsonify({"success": False, "message": str(e)}), 500

# # === STATIC FILE ROUTES ===
# @app.route('/')
# def serve_index():
#     if not request.cookies.get('user_nickname'): return redirect(url_for('serve_login'))
#     return send_from_directory(FRONT_DIR, 'main.html') 

# @app.route('/map')
# def serve_map():
#     if not request.cookies.get('user_nickname'): return redirect(url_for('serve_login'))
#     # Đảm bảo file này là 'map.html' nằm trong folder Front
#     return send_from_directory(FRONT_DIR, 'map.html')

# @app.route('/login')
# def serve_login(): return send_from_directory(FRONT_DIR, 'Login.html')

# @app.route('/register')
# def serve_register(): return send_from_directory(FRONT_DIR, 'Register.html')
    
# @app.route('/profile')
# def serve_profile():
#     if not request.cookies.get('user_nickname'): return redirect(url_for('serve_login'))
#     return send_from_directory(FRONT_DIR, 'profile.html') 

# @app.route('/json/GeminiAPIResponse/<path:filename>')
# def serve_gemini_json(filename): return send_from_directory(os.path.join(JSON_DIR, 'GeminiAPIResponse'), filename)

# @app.route('/json/GoogleMapAPIResponse/<path:filename>')
# def serve_maps_json(filename): return send_from_directory(os.path.join(JSON_DIR, 'GoogleMapAPIResponse'), filename)

# # --- 8. CHẠY SERVER ---
# if __name__ == '__main__':
#     init_db() 
#     logging.info(f"--- SERVER RUNNING @ http://127.0.0.1:5000 ---")
#     app.run(debug=True, port=5000, use_reloader=False)

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
import weather_ai

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

# --- 3. KHỞI TẠO DATABASE ---
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Bảng users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')

        # Bảng favorites (Lưu lộ trình yêu thích)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            plan_title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, file_path, plan_title) 
        );
        ''')

        conn.commit()
        conn.close()
        logging.info("Database (users & favorites) đã được khởi tạo thành công.")
    except Exception as e:
        logging.error(f"LỖI khi khởi tạo database: {e}")

# --- 4. KHỞI TẠO FLASK SERVER ---
app = Flask(__name__)
CORS(app)  
logging.info("--- KHỞI TẠO FLASK SERVER VÀ CẤU HÌNH CORS ---")

# --- 5. BỘ NHỚ JOB ---
jobs = {}

# --- 6. HÀM TÁC VỤ NỀN (ĐÃ SỬA ĐỂ TỐI ƯU TỐC ĐỘ) ---
def run_the_whole_job(job_id, data):
    try:
        logging.info(f"[JOB: {job_id}] --- Bắt đầu tác vụ chạy nền ---")
        
        NEW_USER_LOCATION_DICT = data['location']
        USER_PREFERENCES = data['preferences']
        NEW_TRIP_DURATION = data['duration']
        
        # === [SỬA ĐỔI] KIỂM TRA FILE MAP CŨ ĐỂ BỎ QUA API MAPS ===
        existing_map_path = data.get('existing_map_path')
        generated_maps_filepath = None

        if existing_map_path:
            # Đường dẫn từ frontend là tương đối (json/...), cần chuyển sang tuyệt đối
            abs_map_path = os.path.join(PROJECT_ROOT, existing_map_path)
            if os.path.exists(abs_map_path):
                generated_maps_filepath = abs_map_path
                logging.info(f"[JOB: {job_id}] ⏩ Tái sử dụng file Map cũ (Bỏ qua Search): {generated_maps_filepath}")
            else:
                logging.warning(f"[JOB: {job_id}] File map cũ không tồn tại, sẽ tìm kiếm lại.")

        # Phase 1: Maps (Chỉ chạy nếu chưa có file map)
        if not generated_maps_filepath:
            logging.info(f"[JOB: {job_id}] 🔎 Đang gọi Google Maps API (Tìm kiếm mới)...")
            NEW_USER_RADIUS = 5000  
            NEW_USER_LOCATION_STRING = f"{NEW_USER_LOCATION_DICT['lat']},{NEW_USER_LOCATION_DICT['lng']}"
            
            generated_maps_filepath = api_fetcher.run_search_and_save(
                USER_PREFERENCES,
                NEW_USER_LOCATION_STRING,
                NEW_USER_RADIUS
            )
        
        if not generated_maps_filepath:
            raise Exception("Không tìm thấy địa điểm (Google Maps API lỗi hoặc không có kết quả).")

        logging.info(f"[JOB: {job_id}] ✅ Maps OK: {generated_maps_filepath}")

        # Phase 2: Gemini
        logging.info(f"[JOB: {job_id}] 🧠 Đang gọi Gemini API...")
        generated_plan_filepath = gemini_planner.create_trip_plan_from_file(
            places_input_filepath=generated_maps_filepath,
            user_location_dict=NEW_USER_LOCATION_DICT,
            requested_duration_text=NEW_TRIP_DURATION
        )
        if not generated_plan_filepath:
            raise Exception("Lỗi khi tạo kế hoạch với Gemini.")

        logging.info(f"[JOB: {job_id}] ✅ Gemini OK: {generated_plan_filepath}")

        # Tạo URL trả về
        plan_filename = Path(generated_plan_filepath).name
        map_filename = Path(generated_maps_filepath).name
        
        plan_file_url = f"/json/GeminiAPIResponse/{plan_filename}"
        
        # Trả về đường dẫn tương đối của file map để frontend lưu lại (cho nút "Tạo thêm")
        # Lưu ý: dùng dấu gạch chéo / chuẩn web
        map_file_reference = f"json/GoogleMapAPIResponse/{map_filename}"

        jobs[job_id] = {
            "status": "complete",
            "planFile": plan_file_url,
            "mapFileReference": map_file_reference # <-- Trả về cái này cho frontend
        }
        logging.info(f"[JOB: {job_id}] --- HOÀN THÀNH ---")

    except Exception as e:
        logging.error(f"[JOB: {job_id}] --- THẤT BẠI: {e} ---", exc_info=True)
        jobs[job_id] = {
            "status": "error",
            "error": str(e)
        }

# --- 7. API ROUTES ---

# === JOB ROUTES ===
@app.route('/api/start-job', methods=['POST', 'OPTIONS']) 
def handle_start_job():
    if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)
    
    data = request.json
    if not data: return jsonify({"success": False, "error": "No data"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running"}
    
    thread = threading.Thread(target=run_the_whole_job, args=(job_id, data))
    thread.start() 

    return jsonify({"success": True, "job_id": job_id}), 202

@app.route('/api/check-status', methods=['GET']) 
def handle_check_status():
    job_id = request.args.get('job_id')
    job = jobs.get(job_id)
    if not job: return jsonify({"success": False, "error": "Không tìm thấy Job ID"}), 404
    return jsonify({"success": True, "data": job}), 200

# === AUTH ROUTES (GIỮ NGUYÊN) ===
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def handle_register():
    if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)
        
    data = request.json
    nickname, email, password = data.get('nickname'), data.get('email'), data.get('password')

    if not nickname or not email or not password:
        return jsonify({"success": False, "message": "Thiếu thông tin."}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (nickname, email, password_hash) VALUES (?, ?, ?)", 
                       (nickname, email, generate_password_hash(password)))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Đăng ký thành công!"}), 200
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Email đã tồn tại."}), 409
    except Exception:
        return jsonify({"success": False, "message": "Lỗi server."}), 500

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def handle_login():
    if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)

    data = request.json
    email, password = data.get('email'), data.get('password')
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            response = make_response(jsonify({"success": True, "message": "Đăng nhập thành công!", "nickname": user['nickname']}))
            response.set_cookie('user_nickname', user['nickname'], max_age=3600*24) 
            return response, 200
        else:
            return jsonify({"success": False, "message": "Sai email hoặc mật khẩu."}), 401
    except Exception:
        return jsonify({"success": False, "message": "Lỗi server."}), 500

@app.route('/api/logout', methods=['POST', 'OPTIONS'])
def handle_logout():
    if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)
    response = make_response(jsonify({"success": True, "message": "Đã đăng xuất"}))
    response.delete_cookie('user_nickname')
    return response, 200

@app.route('/api/profile', methods=['GET'])
def handle_get_profile():
    user_nickname = request.cookies.get('user_nickname')
    if not user_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT nickname, email FROM users WHERE nickname = ?", (user_nickname,))
        user = cursor.fetchone()
        conn.close()
        
        if user: return jsonify({"success": True, "nickname": user['nickname'], "email": user['email']})
        else: return jsonify({"success": False, "message": "Không tìm thấy user"}), 404
    except Exception:
        return jsonify({"success": False, "message": "Lỗi server."}), 500

@app.route('/api/profile/update', methods=['POST', 'OPTIONS'])
def handle_update_profile():
    if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)

    current_nickname = request.cookies.get('user_nickname')
    if not current_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    data = request.json
    new_nickname = data.get('nickname')
    new_password = data.get('password') 

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if new_password:
            cursor.execute("UPDATE users SET nickname = ?, password_hash = ? WHERE nickname = ?",
                           (new_nickname, generate_password_hash(new_password), current_nickname))
        else:
            cursor.execute("UPDATE users SET nickname = ? WHERE nickname = ?",
                           (new_nickname, current_nickname))
        conn.commit()
        conn.close()
        
        response = make_response(jsonify({"success": True, "message": "Cập nhật thành công!"}))
        response.set_cookie('user_nickname', new_nickname, max_age=3600*24)
        return response, 200
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Nickname đã tồn tại."}), 409
    except Exception:
        return jsonify({"success": False, "message": "Lỗi server."}), 500

# === FAVORITES ROUTES (GIỮ NGUYÊN) ===

@app.route('/api/favorites/add', methods=['POST', 'OPTIONS'])
def handle_add_favorite():
    if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)

    user_nickname = request.cookies.get('user_nickname')
    if not user_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401

    data = request.json
    raw_path = data.get('file_path') 
    plan_title = data.get('plan_title')

    if not raw_path or not plan_title:
        return jsonify({"success": False, "message": "Thiếu thông tin"}), 400
    
    filename = os.path.basename(raw_path)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE nickname = ?", (user_nickname,))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("INSERT OR IGNORE INTO favorites (user_id, file_path, plan_title) VALUES (?, ?, ?)", 
                           (user['id'], filename, plan_title))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Đã lưu vào mục yêu thích!"}), 200
        else:
            return jsonify({"success": False, "message": "User không tồn tại"}), 404
    except Exception as e:
        logging.error(f"Lỗi lưu fav: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/favorites', methods=['GET'])
def handle_get_favorites():
    user_nickname = request.cookies.get('user_nickname')
    if not user_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.id, f.file_path, f.plan_title, f.created_at 
            FROM favorites f
            JOIN users u ON f.user_id = u.id
            WHERE u.nickname = ?
            ORDER BY f.created_at DESC
        """, (user_nickname,))
        
        rows = cursor.fetchall()
        favorites = [dict(row) for row in rows]
        conn.close()
        return jsonify({"success": True, "favorites": favorites}), 200
    except Exception as e:
        logging.error(f"Lỗi lấy fav: {e}")
        return jsonify({"success": False, "message": "Lỗi server"}), 500

@app.route('/api/favorites/delete', methods=['POST', 'OPTIONS'])
def handle_delete_favorite():
    if request.method == 'OPTIONS': return make_response(jsonify({"message": "OK"}), 200)

    user_nickname = request.cookies.get('user_nickname')
    if not user_nickname: return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401

    data = request.json
    raw_path = data.get('file_path') 
    plan_title = data.get('plan_title')

    if not raw_path or not plan_title:
        return jsonify({"success": False, "message": "Thiếu thông tin"}), 400
    
    filename = os.path.basename(raw_path)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE nickname = ?", (user_nickname,))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("""
                DELETE FROM favorites 
                WHERE user_id = ? AND file_path = ? AND plan_title = ?
            """, (user['id'], filename, plan_title))
            
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Đã xóa khỏi mục yêu thích"}), 200
        else:
            return jsonify({"success": False, "message": "User không tồn tại"}), 404
    except Exception as e:
        logging.error(f"Lỗi xóa fav: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# === STATIC FILE ROUTES ===
@app.route('/')
def serve_index():
    if not request.cookies.get('user_nickname'): return redirect(url_for('serve_login'))
    return send_from_directory(FRONT_DIR, 'main.html') 

@app.route('/map')
def serve_map():
    if not request.cookies.get('user_nickname'): return redirect(url_for('serve_login'))
    return send_from_directory(FRONT_DIR, 'map.html')

@app.route('/login')
def serve_login(): return send_from_directory(FRONT_DIR, 'Login.html')

@app.route('/register')
def serve_register(): return send_from_directory(FRONT_DIR, 'Register.html')
    
@app.route('/profile')
def serve_profile():
    if not request.cookies.get('user_nickname'): return redirect(url_for('serve_login'))
    return send_from_directory(FRONT_DIR, 'profile.html') 

@app.route('/json/GeminiAPIResponse/<path:filename>')
def serve_gemini_json(filename): return send_from_directory(os.path.join(JSON_DIR, 'GeminiAPIResponse'), filename)

@app.route('/json/GoogleMapAPIResponse/<path:filename>')
def serve_maps_json(filename): return send_from_directory(os.path.join(JSON_DIR, 'GoogleMapAPIResponse'), filename)

@app.route('/api/weather', methods=['GET'])
def handle_get_weather():
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    
    if not lat or not lng:
        return jsonify({"success": False, "message": "Thiếu tọa độ"}), 400
        
    try:
        # Gọi hàm từ file weather_ai.py
        result = weather_ai.get_weather_advice(float(lat), float(lng))
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Lỗi API Weather: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
# --- 8. CHẠY SERVER ---

if __name__ == '__main__':
    init_db() 
    logging.info(f"--- SERVER RUNNING @ http://127.0.0.1:5000 ---")
    app.run(debug=True, port=5000, use_reloader=False)