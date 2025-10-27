import requests
import time
import json
import os
import datetime
from multiprocessing.dummy import Pool as ThreadPool
from functools import partial

# --- CẤU HÌNH CỦA BẠN ---
API_KEY = "AIzaSyAmbdRFOMwNlwiUD-LEwTvvJ6Twb0JlpmU"
USER_LOCATION = "34.6872571,135.5258546" # (Ví dụ: Tokyo Tower)
USER_RADIUS = 30000

# ⚠️ QUAN TRỌNG: Chỉ định các trường (fields) bạn muốn lấy
# Tách các trường Basic (miễn phí) và các trường trả phí
# (Trường 'place_id', 'name', 'geometry' đã có từ NearbySearch)
# ⚠️ QUAN TRỌNG: Chỉ định các trường (fields) bạn muốn lấy

PLACE_DETAILS_FIELDS = [
    # --- Basic Data (Miễn phí) ---
    "place_id",      # <--- THÊM DÒNG NÀY VÀO
    
    # --- Contact Data (Tính phí) ---
    "formatted_phone_number",
    "website",
    
    # --- Atmosphere Data (Tính phí) ---
    "opening_hours", 
    "rating",        
    "reviews",       # (Của bạn đã có)
    "user_ratings_total", 
    "price_level"    
]
# Chuyển thành string để truyền vào API
FIELDS_STRING = ",".join(PLACE_DETAILS_FIELDS)
# -------------------------

# 🧠 Bước 1: "Bản đồ" ánh xạ
preference_to_api_map = {
    "pref_ramen": {"type": "restaurant", "keyword": "ラーメン"},
    "pref_park": {"type": "park", "keyword": ""},
    "pref_museum_art": {"type": "art_gallery", "keyword": ""},
    "pref_cafe": {"type": "cafe", "keyword": ""},
    "pref_sento": {"type": "spa", "keyword": ""},
    "pref_late_night": {"strategy": "FILTER_BY_OPENING_HOURS"}
}

# ⚙️ Bước 2: Worker cho Phase 1 (NearbySearch)
# (Giữ nguyên code từ trước)
def fetch_places_for_job(job, location, radius):
    endpoint_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    all_results_for_this_job = []
    
    params = {
        'location': location,
        'radius': radius,
        'type': job['type'],
        'keyword': job.get('keyword', ''),
        'language': 'ja',
        'key': API_KEY
    }
    page_count = 1
    
    # print(f"[NearbyWorker] Bắt đầu job: {job}...") # (Tắt bớt log cho đỡ rối)

    while True:
        try:
            response = requests.get(endpoint_url, params=params)
            if response.status_code != 200: break
            data = response.json()
            if data['status'] == 'OK':
                all_results_for_this_job.extend(data['results'])
                next_page_token = data.get('next_page_token')
                if next_page_token:
                    page_count += 1
                    time.sleep(2)
                    params = {'pagetoken': next_page_token, 'key': API_KEY}
                else:
                    break
            else:
                break
        except Exception:
            break
            
    # print(f"[NearbyWorker] Hoàn thành job: {job}. Tìm thấy {len(all_results_for_this_job)} kết quả.")
    return all_results_for_this_job

# ⚙️ Bước 3 (MỚI): Worker cho Phase 2 (PlaceDetails)
# ⚙️ Bước 3: Worker cho Phase 2 (PlaceDetails) - ĐÃ DỌN DẸP
def fetch_place_details_for_id(place_id, fields_string):
    """
    Thực thi MỘT lệnh gọi PlaceDetails cho một place_id.
    """
    endpoint_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        'place_id': place_id,
        'fields': fields_string,
        'language': 'ja',
        'key': API_KEY
    }
    
    try:
        response = requests.get(endpoint_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK':
                # print(f"[DetailsWorker] Lấy thành công chi tiết cho: {place_id}") # Tắt bớt log
                return data['result'] # Chỉ trả về kết quả
        
        # Nếu thất bại
        print(f"[DetailsWorker LỖI] {place_id}: {response.text}")
        return None

    except Exception as e:
        print(f"[DetailsWorker LỖI KẾT NỐI] {place_id}: {e}")
        return None
    
# 🏃‍♂️ Bước 4 (CẬP NHẬT): Hàm Main để điều phối
def find_and_enrich_places(selected_ids, location, radius, fields_to_request_str):
    
    # === PHASE 1: DISCOVERY (Chạy NearbySearch song song) ===
    
    jobs_to_run = []
    logic_filters = []
    for pref_id in selected_ids:
        strategy = preference_to_api_map.get(pref_id)
        if strategy:
            if "type" in strategy: jobs_to_run.append(strategy)
            elif "strategy" in strategy: logic_filters.append(strategy['strategy'])

    if not jobs_to_run:
        print("Không có sở thích nào cần gọi API.")
        return [], logic_filters

    print(f"--- PHASE 1: Đang chạy {len(jobs_to_run)} NearbySearch jobs song song ---")
    
    pool_size_nearby = 5
    pool_nearby = ThreadPool(pool_size_nearby)
    worker_nearby = partial(fetch_places_for_job, location=location, radius=radius)
    
    results_list_of_lists = pool_nearby.map(worker_nearby, jobs_to_run)
    
    pool_nearby.close()
    pool_nearby.join()

    # Gộp và Lọc trùng
    all_basic_results = {} # Dùng dictionary để lọc trùng ngay lập tức
    for sublist in results_list_of_lists:
        for place in sublist:
            place_id = place.get('place_id')
            if place_id and place_id not in all_basic_results:
                all_basic_results[place_id] = place

    unique_basic_results = list(all_basic_results.values())
    unique_place_ids = list(all_basic_results.keys())
    
    if not unique_place_ids:
        print("Phase 1 không tìm thấy địa điểm nào.")
        return [], logic_filters

    print(f"--- PHASE 1: Hoàn thành. Tìm thấy {len(unique_basic_results)} địa điểm duy nhất. ---")

    # === PHASE 2: ENRICHMENT (Chạy PlaceDetails song song) ===
    
    print(f"\n--- PHASE 2: Đang lấy chi tiết cho {len(unique_place_ids)} địa điểm song song ---")
    
    # Có thể dùng nhiều luồng hơn cho Details vì nó nhanh hơn
    pool_size_details = 10 
    pool_details = ThreadPool(pool_size_details)
    
    # Gói hàm worker và tham số 'fields_string'
    worker_details = partial(fetch_place_details_for_id, fields_string=fields_to_request_str)
    
    # 'detailed_results_list' sẽ chứa các dictionary (hoặc None nếu lỗi)
    detailed_results_list = pool_details.map(worker_details, unique_place_ids)
    
    pool_details.close()
    pool_details.join()

    print(f"--- PHASE 2: Hoàn thành. ---")

    # === GỘP KẾT QUẢ CUỐI CÙNG ===
    
    # Tạo một "bản đồ" tra cứu nhanh kết quả Details
    details_map = {res['place_id']: res for res in detailed_results_list if res and 'place_id' in res}
    
    final_merged_list = []
    for basic_place in unique_basic_results:
        place_id = basic_place['place_id']
        if place_id in details_map:
            # Gộp data: Lấy dict cơ bản và "cập nhật" thêm dict chi tiết
            basic_place.update(details_map[place_id])
            final_merged_list.append(basic_place)
        else:
            # Nếu vì lý do gì đó mà Details bị lỗi,
            # chúng ta vẫn giữ lại thông tin cơ bản
            basic_place['details_fetch_failed'] = True
            final_merged_list.append(basic_place)
            
    print(f"\nĐã gộp thành công {len(final_merged_list)} địa điểm với thông tin chi tiết.")
    
    return final_merged_list, logic_filters

# 🏁 Bước 5: Chạy thử VÀ LƯU FILE
if __name__ == "__main__":
    
    user_choices = ['pref_ramen', 'pref_park', 'pref_museum_art']
    
    start_time = time.time()
    
    # Chạy hàm chính
    final_places, filters_to_apply = find_and_enrich_places(
        user_choices, 
        USER_LOCATION, 
        USER_RADIUS, 
        FIELDS_STRING
    )
    
    end_time = time.time()
    print(f"\n--- Tổng thời gian (cả 2 phase): {end_time - start_time:.2f} giây ---")
    print(f"Các bộ lọc logic cần áp dụng: {filters_to_apply}")
    
    # --- PHẦN LƯU FILE ---
    if final_places:
        OUTPUT_DIR = "/Users/quannguyen/チーム制作/Rakutabi/json/test"
        
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        safe_prefs = "_".join(user_choices)
        FILENAME = f"EnrichedSearch_{safe_prefs}_{timestamp}.json" # Tên file mới
        OUTPUT_FILENAME = os.path.join(OUTPUT_DIR, FILENAME)

        print(f"\nĐang lưu {len(final_places)} kết quả (đã gộp) vào: {OUTPUT_FILENAME}...")
        
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(final_places, f, indent=4, ensure_ascii=False)
            print("Đã lưu file thành công!")
        
        except Exception as e:
            print(f"LỖI khi lưu file: {e}")
            
    else:
        print("\nKhông có kết quả nào để lưu.")