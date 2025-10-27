import requests
import json
import os
import datetime

# --- THAY ĐỔI CÁC GIÁ TRỊ NÀY ---
API_KEY = "AIzaSyAmbdRFOMwNlwiUD-LEwTvvJ6Twb0JlpmU" 

# Place ID bạn muốn tra cứu (Bạn lấy ID này từ Nearby Search hoặc Geocoding)
# Ví dụ: Place ID của Tokyo Tower
PLACE_ID_TO_SEARCH = "ChIJN1t_tDeuEmsRUsoyG83frY4"

# Danh sách các trường (fields) bạn muốn lấy thông tin
# XÓA HOẶC THÊM CÁC TRƯỜNG BẠN MUỐN ĐỂ TIẾT KIỆM CHI PHÍ
# Xem chi tiết: https://developers.google.com/maps/documentation/places/web-service/place-details
FIELDS_TO_REQUEST = [
    # --- Basic Data (Miễn phí) ---
    "place_id",      # ID của địa điểm
    "name",          # Tên
    "geometry",      # Chứa "location" (lat, lng)
    "formatted_address", # Địa chỉ đầy đủ
    "types",         # Danh sách các loại (restaurant, park, v.v.)
    "business_status", # Trạng thái (OPERATIONAL, CLOSED_TEMPORARILY...)
    
    # --- Contact Data (Tính phí) ---
    "formatted_phone_number", # Số điện thoại
    "website",                # Trang web

    # --- Atmosphere Data (Tính phí) ---
    "opening_hours", # Giờ mở cửa (current_opening_hours)
    "rating",        # Đánh giá (1.0 - 5.0)
    "reviews",       # Các bài đánh giá chi tiết
    "user_ratings_total", # Tổng số lượng đánh giá
    "price_level",   # Mức giá (0-4)
    "photos"         # Danh sách ảnh
]

# Đường dẫn đến thư mục bạn muốn lưu file
OUTPUT_DIR = "/Users/quannguyen/チーム制作/Rakutabi/json/PlaceDetailAPI"
# ------------------------------------

# ===== TỰ ĐỘNG TẠO TÊN FILE =====
now = datetime.datetime.now()
timestamp = now.strftime("%Y%m%d_%H%M%S")

# Tên file sẽ là [PlaceID]_[Timestamp].json
FILENAME = f"{PLACE_ID_TO_SEARCH}_{timestamp}.json"
OUTPUT_FILENAME = os.path.join(OUTPUT_DIR, FILENAME)
# ==================================

# URL của Place Details API
endpoint_url = "https://maps.googleapis.com/maps/api/place/details/json"

# Chuyển đổi list các fields thành một chuỗi (string) ngăn cách bởi dấu phẩy
fields_string = ",".join(FIELDS_TO_REQUEST)

# Các tham số (parameters) cho API call
params = {
    'place_id': PLACE_ID_TO_SEARCH,
    'fields': fields_string,
    'language': 'ja', # Lấy thông tin bằng tiếng Nhật
    'key': API_KEY
}

print(f"Đang lấy thông tin chi tiết cho Place ID: '{PLACE_ID_TO_SEARCH}'...")
print(f"Các trường (fields) yêu cầu: {fields_string}")

try:
    # Gửi request GET đến API
    response = requests.get(endpoint_url, params=params)

    if response.status_code == 200:
        data = response.json()
        
        # Kiểm tra trạng thái từ chính API của Google
        if data['status'] == 'OK':
            print("Lấy thông tin thành công! Đang lưu kết quả...")

            # Tạo thư mục (và các thư mục cha) nếu nó chưa tồn tại
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            
            # Ghi file
            with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as json_file:
                # 'data['result']' là dictionary chứa thông tin địa điểm
                json.dump(data['result'], json_file, indent=4, ensure_ascii=False)
            
            print(f"Đã lưu thành công vào: '{OUTPUT_FILENAME}'")
            
        else:
            print(f"Lỗi từ API Google: {data['status']}")
            if 'error_message' in data:
                print(f"Chi tiết: {data['error_message']}")

    else:
        print(f"Request thất bại, Status Code: {response.status_code}")
        print(f"Response: {response.text}")

except requests.exceptions.RequestException as e:
    # Lỗi nếu không kết nối được mạng
    print(f"Lỗi kết nối: {e}")