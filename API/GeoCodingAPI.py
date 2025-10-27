import requests
import json
import os
import datetime  # <-- Thêm thư viện datetime
import re        # <-- Thêm thư viện re (Regex) để làm sạch tên file

# --- THAY ĐỔI CÁC GIÁ TRỊ NÀY ---
API_KEY = "AIzaSyAmbdRFOMwNlwiUD-LEwTvvJ6Twb0JlpmU" 

# Địa chỉ bạn muốn geocode (có thể thay đổi)
# Ví dụ: "Tokyo Tower, Japan" hoặc "東京タワー"
ADDRESS_TO_SEARCH = "東京タワー"

# Đường dẫn đến thư mục bạn muốn lưu file
OUTPUT_DIR = "/Users/quannguyen/チーム制作/Rakutabi/json/GeoCodingAPI"
# ------------------------------------

# ===== TỰ ĐỘNG TẠO TÊN FILE =====

# 1. Lấy ngày giờ hiện tại
now = datetime.datetime.now()
# Format: YYYYMMDD_HHMMSS (ví dụ: 20251027_143055)
timestamp = now.strftime("%Y%m%d_%H%M%S")

# 2. Làm sạch (sanitize) tên địa chỉ để dùng làm tên file
# Thay thế bất kỳ ký tự nào không phải là chữ, số, dấu gạch dưới, gạch ngang, hoặc dấu chấm
# bằng một dấu gạch dưới '_'
# (Điều này để tránh lỗi nếu địa chỉ có dấu / , \ : * ? " < > |)
safe_address = re.sub(r'[^\w\-_.]', '_', ADDRESS_TO_SEARCH)

# 3. Tạo tên file cuối cùng
# Ví dụ: "東京タワー_20251027_143055.json"
FILENAME = f"{safe_address}_{timestamp}.json"

# Kết hợp đường dẫn thư mục và tên file
OUTPUT_FILENAME = os.path.join(OUTPUT_DIR, FILENAME)

# ==================================

# URL của Geocoding API
endpoint_url = "https://maps.googleapis.com/maps/api/geocode/json"

# Các tham số (parameters) cho API call
params = {
    'address': ADDRESS_TO_SEARCH,
    'key': API_KEY,
    'language': 'ja'
}

print(f"Đang tìm kiếm geocode cho: '{ADDRESS_TO_SEARCH}'...")
print(f"Sẽ lưu kết quả vào: '{OUTPUT_FILENAME}'")

try:
    # Gửi request GET đến API
    response = requests.get(endpoint_url, params=params)

    if response.status_code == 200:
        data = response.json()
        
        if data['status'] == 'OK':
            print("Tìm kiếm thành công! Đang lưu kết quả...")

            # Tạo thư mục (và các thư mục cha) nếu nó chưa tồn tại
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            
            # Ghi file
            with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=4, ensure_ascii=False)
            
            print(f"Đã lưu thành công!")
            
            location = data['results'][0]['geometry']['location']
            print(f"Tọa độ (Lat, Lng): {location['lat']}, {location['lng']}")
            
        else:
            print(f"Lỗi từ API Google: {data['status']}")
            if 'error_message' in data:
                print(f"Chi tiết: {data['error_message']}")

    else:
        print(f"Request thất bại, Status Code: {response.status_code}")
        print(f"Response: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"Lỗi kết nối: {e}")