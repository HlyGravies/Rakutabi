import exifread
from geopy.geocoders import Nominatim

def get_decimal_from_dms(dms, ref):
    """Chuyển đổi tọa độ từ DMS (Độ, Phút, Giây) sang dạng thập phân."""
    degrees = float(dms[0].num) / float(dms[0].den)
    minutes = float(dms[1].num) / float(dms[1].den)
    seconds = float(dms[2].num) / float(dms[2].den)
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

# --- PHẦN MỚI THÊM VÀO ---
def get_location_name(lat, lon):
    """Dùng geopy để tìm tên địa điểm từ tọa độ."""
    geolocator = Nominatim(user_agent="my_location_finder_app") # Đặt tên bất kỳ cho app của bạn
    try:
        # Dùng language='ja' để ưu tiên kết quả tiếng Nhật
        location = geolocator.reverse((lat, lon), language='ja')
        if location:
            return location.address
        else:
            return "Không tìm thấy địa điểm."
    except Exception as e:
        return f"Đã xảy ra lỗi: {e}"
# -------------------------

# Thay "path/to/your/image.HEIC" bằng đường dẫn thật của bạn
image_path = "F:\PythonProject\Rakutabi\py\IMG_2719.HEIC" 

with open(image_path, "rb") as f:
    tags = exifread.process_file(f)

# Lấy dữ liệu GPS
lat_tag = tags.get("GPS GPSLatitude")
lat_ref_tag = tags.get("GPS GPSLatitudeRef")
lon_tag = tags.get("GPS GPSLongitude")
lon_ref_tag = tags.get("GPS GPSLongitudeRef")
time_tag = tags.get("EXIF DateTimeOriginal")

if lat_tag and lon_tag and lat_ref_tag and lon_ref_tag:
    lat_decimal = get_decimal_from_dms(lat_tag.values, lat_ref_tag.values)
    lon_decimal = get_decimal_from_dms(lon_tag.values, lon_ref_tag.values)
    
    print(f"Tọa độ thập phân: {lat_decimal}, {lon_decimal}")
    
    # --- GỌI HÀM MỚI ĐỂ LẤY TÊN ĐỊA ĐIỂM ---
    location_name = get_location_name(lat_decimal, lon_decimal)
    print(f"Địa điểm tương ứng: {location_name}")
    # ------------------------------------

    print(f"Link Google Maps: https://www.google.com/maps?q={lat_decimal},{lon_decimal}")

if time_tag:
    print(f"Thời gian chụp: {time_tag}")