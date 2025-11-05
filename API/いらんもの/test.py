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
    "price_level",
    "photos"    
]
# Chuyển thành string để truyền vào API
FIELDS_STRING = ",".join(PLACE_DETAILS_FIELDS)
# -------------------------

# 🧠 Bước 1: "Bản đồ" ánh xạ
# 🧠 "Bản đồ" ánh xạ đầy đủ (Full Preference Map)
# Ánh xạ ID sở thích của bạn tới chiến lược gọi Google Places API
preference_to_api_map = {
    # === 観光・探索 (Tham quan) ===
    "pref_landmark": {"type": "tourist_attraction", "keyword": "名所 ランドマーク"},
    "pref_shrine": {"type": "tourist_attraction", "keyword": "神社仏閣"},
    "pref_historical": {"type": "tourist_attraction", "keyword": "歴史的建造物 史跡"},
    "pref_viewpoint": {"type": "tourist_attraction", "keyword": "展望台 ビュースポット"},
    "pref_pilgrimage": {"type": "tourist_attraction", "keyword": "聖地巡礼"},
    "pref_tower": {"type": "tourist_attraction", "keyword": "タワー 高層ビル"},
    "pref_hidden_gem": {"type": "tourist_attraction", "keyword": "穴場スポット"},
    "pref_free_spot": {"strategy": "FILTER_BY_PRICE_LEVEL", "notes": "Lọc địa điểm có price_level=0 hoặc không có"},
    "pref_museum_art": {"type": "art_gallery"},
    "pref_museum_history": {"type": "museum"},

    # === リラックス・休憩 (Thư giãn) ===
    "pref_cafe": {"type": "cafe"},
    "pref_kissaten": {"type": "cafe", "keyword": "喫茶店 レトロ"},
    "pref_park": {"type": "park"},
    "pref_garden": {"type": "park", "keyword": "庭園"},
    "pref_waterside": {"type": "park", "keyword": "水辺 川 湖"},
    "pref_footbath": {"type": "spa", "keyword": "足湯"},
    "pref_library": {"type": "library"},
    "pref_net_cafe": {"type": "cafe", "keyword": "漫画喫茶 ネットカフェ"},
    "pref_sento": {"type": "spa"}, # 'spa' là type đúng cho sento/onsen
    "pref_massage": {"type": "spa", "keyword": "マッサージ"},

    # === 癒し・ヒーリング (Chữa lành) ===
    "pref_nature_walk": {"type": "park", "keyword": "森林浴 自然散策"},
    "pref_botanical_garden": {"type": "zoo", "keyword": "植物園"}, # Thường bị gộp vào 'zoo' hoặc 'park'
    "pref_aroma": {"type": "spa", "keyword": "アロマ お香"},
    "pref_spa_este": {"type": "spa", "keyword": "スパ エステ"},
    "pref_yoga": {"type": "gym", "keyword": "ヨガ"},
    "pref_quiet_shrine": {"type": "tourist_attraction", "keyword": "静か 神社"},
    "pref_animal_cafe": {"type": "cafe", "keyword": "動物カフェ"},
    "pref_music_classic": {"type": "tourist_attraction", "keyword": "音楽鑑賞 クラシック"},
    "pref_planetarium": {"type": "museum", "keyword": "プラネタリウム"},

    # === グルメ・食事 (Ẩm thực) ===
    "pref_street_food": {"type": "meal_takeaway", "keyword": "食べ歩き"},
    "pref_local_gourmet": {"type": "restaurant", "keyword": "B級グルメ ご当地グルメ"},
    "pref_set_meal": {"type": "restaurant", "keyword": "ローカル食堂 定食屋"},
    "pref_sweets": {"type": "cafe", "keyword": "スイーツ デザート"},
    "pref_bakery": {"type": "bakery"},
    "pref_ramen": {"type": "restaurant", "keyword": "ラーメン"},
    "pref_sushi": {"type": "restaurant", "keyword": "寿司"},
    "pref_ethnic": {"type": "restaurant", "keyword": "エスニック料理"},
    "pref_izakaya": {"type": "bar", "keyword": "居酒屋 立ち飲み"},
    "pref_allyoucan": {"type": "restaurant", "keyword": "食べ放題 飲み放題"},
    "pref_late_night": {"strategy": "FILTER_BY_OPENING_HOURS", "notes": "Lọc địa điểm open_now vào ban đêm"},

    # === 散策・街歩き (Dạo phố) ===
    "pref_alley": {"type": "tourist_attraction", "keyword": "路地裏 横丁"},
    "pref_architecture": {"type": "tourist_attraction", "keyword": "建築巡り"},
    "pref_shotengai": {"type": "shopping_mall", "keyword": "商店街"},
    "pref_slope_stairs": {"type": "tourist_attraction", "keyword": "坂道 階段"},
    "pref_market": {"type": "store", "keyword": "市場 マーケット"},
    "pref_window_shopping": {"type": "shopping_mall"},
    "pref_riverside": {"type": "park", "keyword": "川沿い 海辺 散歩"},
    "pref_night_walk": {"strategy": "LOGIC_ONLY", "notes": "Đây là 1 route, không phải 1 địa điểm"},

    # === 学び・体験 (Học hỏi) ===
    "pref_art_gallery": {"type": "art_gallery"},
    "pref_museum": {"type": "museum"},
    "pref_aquarium_zoo": {"type": ["aquarium", "zoo"]}, # Xử lý đặc biệt: gọi 2 API
    "pref_workshop": {"type": "tourist_attraction", "keyword": "ワークショップ 文化体験"},
    "pref_crafts": {"type": "store", "keyword": "伝統工芸"},
    "pref_factory_tour": {"type": "tourist_attraction", "keyword": "工場見学"},
    "pref_cinema": {"type": "movie_theater"},
    "pref_theater_live": {"type": "night_club", "keyword": "劇場 ライブハウス"},
    "pref_seminar": {"type": "university", "keyword": "講演 セミナー"},

    # === ショッピング (Mua sắm) ===
    "pref_souvenir": {"type": "store", "keyword": "お土産"},
    "pref_zakka": {"type": "store", "keyword": "雑貨屋"},
    "pref_select_shop": {"type": "clothing_store", "keyword": "セレクトショップ"},
    "pref_used_clothes": {"type": "clothing_store", "keyword": "古着屋"},
    "pref_department_store": {"type": "department_store"},
    "pref_drugstore": {"type": "drugstore"},
    "pref_100yen_shop": {"type": "store", "keyword": "100円ショップ"},
    "pref_local_supermarket": {"type": "supermarket"},
    "pref_electronics": {"type": "electronics_store"},
    "pref_antique": {"type": "store", "keyword": "骨董品 アンティーク"},

    # === 写真・SNS映え (Chụp ảnh) ===
    "pref_sns_hotspot": {"type": "tourist_attraction", "keyword": "SNSで話題 スポット"},
    "pref_stylish_cafe": {"type": "cafe", "keyword": "おしゃれ カフェ"},
    "pref_cute_sweets": {"type": "cafe", "keyword": "可愛い スイーツ"},
    "pref_street_art": {"type": "tourist_attraction", "keyword": "壁画 ストリートアート"},
    "pref_arch_photo": {"type": "tourist_attraction", "keyword": "印象的な建築"},
    "pref_night_view": {"type": "tourist_attraction", "keyword": "夜景 ライトアップ"},
    "pref_retro_spot": {"type": "tourist_attraction", "keyword": "レトロ ノスタルジック"},
    "pref_scenic_view": {"type": "tourist_attraction", "keyword": "絶景 風景"},

    # === 自然・風景 (Thiên nhiên) ===
    "pref_park_green": {"type": "park"},
    "pref_garden_jp": {"type": "park", "keyword": "日本庭園"},
    "pref_waterside_walk": {"type": "park", "keyword": "水辺"},
    "pref_viewpoint_high": {"type": "tourist_attraction", "keyword": "高台 展望"},
    "pref_botanical": {"type": "zoo", "keyword": "植物園"},
    "pref_seasonal_flower": {"type": "park", "keyword": "季節の花 桜 紅葉"},
    "pref_hiking_light": {"type": "park", "keyword": "ハイキング"},

    # === 気分転換 (Xả stress) ===
    "pref_good_view": {"type": "tourist_attraction", "keyword": "景色の良い場所"},
    "pref_quiet_cafe": {"type": "cafe", "keyword": "静か カフェ"},
    "pref_park_walk": {"type": "park"},
    "pref_karaoke": {"type": "night_club", "keyword": "カラオケ"},
    "pref_game_center": {"type": "amusement_park", "keyword": "ゲームセンター"},
    "pref_batting_center": {"type": "tourist_attraction", "keyword": "バッティングセンター"},
    "pref_bookstore": {"type": "book_store"},

    # === ローカル体験 (Trải nghiệm) ===
    "pref_local_market": {"type": "store", "keyword": "地元の市場"},
    "pref_old_shotengai": {"type": "shopping_mall", "keyword": "昔ながらの商店街"},
    "pref_local_super": {"type": "supermarket"},
    "pref_public_bath": {"type": "spa", "keyword": "銭湯"},
    "pref_yokocho": {"type": "bar", "keyword": "横丁 飲み屋街"},
    "pref_local_diner": {"type": "restaurant", "keyword": "ローカル食堂"},
    "pref_local_event": {"strategy": "LOGIC_ONLY", "notes": "Cần 1 API khác về sự kiện"},

    # === トレンド (Bắt trend) ===
    "pref_sns_trending": {"type": "point_of_interest", "keyword": "SNS 話題"},
    "pref_new_open": {"type": "point_of_interest", "keyword": "新オープン"},
    "pref_trending_gourmet": {"type": "restaurant", "keyword": "流行 グルメ"},
    "pref_popup_store": {"type": "store", "keyword": "ポップアップストア"},
    "pref_collab_cafe": {"type": "cafe", "keyword": "コラボカフェ"},

    # === アクティブ (Năng động) ===
    "pref_walking": {"strategy": "LOGIC_ONLY", "notes": "Là 1 route"},
    "pref_rental_cycle": {"type": "bicycle_store", "keyword": "レンタサイクル"},
    "pref_bouldering": {"type": "gym", "keyword": "ボルダリング"},
    "pref_game_arcade": {"type": "amusement_park", "keyword": "ゲームセンター"},
    "pref_sports_watch": {"type": "stadium"},
    "pref_pool": {"type": "gym", "keyword": "プール"},

    # === 自分にご褒美 (Tự thưởng) ===
    "pref_luxury_sweets": {"type": "cafe", "keyword": "高級 スイーツ パフェ"}, # Lọc thêm price_level
    "pref_good_lunch": {"type": "restaurant", "keyword": "高級 ランチ"}, # Lọc thêm price_level
    "pref_spa_treatment": {"type": "spa", "keyword": "スパ エステ"},
    "pref_brand_shopping": {"type": "department_store", "keyword": "ブランド"},
    "pref_hotel_lounge": {"type": "lodging", "keyword": "ホテル ラウンジ"},
    "pref_luxury_goods": {"type": "store", "keyword": "高級 雑貨"},

    # === 深掘り・マニアック (Chuyên sâu) ===
    "pref_specialty_store": {"type": "store", "keyword": "専門店"},
    "pref_used_bookstore": {"type": "book_store", "keyword": "古書店 古本"},
    "pref_record_store": {"type": "store", "keyword": "レコード店"},
    "pref_theme_cafe": {"type": "cafe", "keyword": "テーマカフェ"},
    "pref_unique_spot": {"type": "tourist_attraction", "keyword": "珍スポット"},
    "pref_mini_theater": {"type": "movie_theater", "keyword": "ミニシアター"},
    "pref_architecture_niche": {"type": "tourist_attraction", "keyword": "マニアック 建築"},

    # === 時間調整 (Giết thời gian) ===
    "pref_station_cafe": {"type": "cafe", "keyword": "駅近"},
    "pref_bookstore_browse": {"type": "book_store"},
    "pref_100yen_drugstore": {"type": ["store", "drugstore"], "keyword": "100円ショップ"}, # Xử lý đặc biệt
    "pref_station_building": {"type": "shopping_mall", "keyword": "駅ビル"},
    "pref_fast_food": {"type": "restaurant", "keyword": "ファストフード"},
    "pref_arcade": {"type": "amusement_park", "keyword": "ゲームセンター"},

    # === 無料・節約 (Tiết kiệm) ===
    "pref_free_observatory": {"type": "tourist_attraction", "keyword": "無料 展望台"},
    "pref_free_museum": {"type": "museum", "keyword": "無料"},
    "pref_public_facility": {"type": ["library", "park"]}, # Xử lý đặc biệt
    "pref_park_large": {"type": "park"},
    "pref_free_samples": {"strategy": "LOGIC_ONLY", "notes": "Không thể tìm bằng API"},
    "pref_window_shopping_main": {"type": "shopping_mall"},

    # === 夜の楽しみ (Ban đêm) ===
    "pref_night_view_spot": {"type": "tourist_attraction", "keyword": "夜景"},
    "pref_bar": {"type": "bar"},
    "pref_izakaya_hopping": {"type": "bar", "keyword": "居酒屋 はしご酒"},
    "pref_night_cafe": {"type": "cafe", "keyword": "夜カフェ"}, # Lọc thêm opening_hours
    "pref_live_house_club": {"type": "night_club"},
    "pref_light_up": {"type": "tourist_attraction", "keyword": "ライトアップ イルミネーション"},
    "pref_night_bowling": {"type": "bowling_alley"},
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