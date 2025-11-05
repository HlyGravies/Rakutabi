import requests
import time
import json
import os
import datetime
from multiprocessing.dummy import Pool as ThreadPool
from functools import partial

# --- CẤU HÌNH CỐ ĐỊNH ---
API_KEY = "AIzaSyAmbdRFOMwNlwiUD-LEwTvvJ6Twb0JlpmU" # ⚠️ Hãy giữ bí mật API Key

# 📍 Cấu hình đường dẫn lưu file:
# Tạo một thư mục 'json_output' ngay bên cạnh file .py này
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "../json/GoogleMapAPIResponse")

# ⚠️ BƯỚC 1: CẬP NHẬT DANH SÁCH FIELDS
PLACE_DETAILS_FIELDS = [
    "place_id", "opening_hours", "photos", "price_level",
    "rating", "reviews", "user_ratings_total", "geometry", "types"
]
FIELDS_STRING = ",".join(PLACE_DETAILS_FIELDS)

# 🧠 "Bản đồ" ánh xạ (Sử dụng bản đồ đầy đủ bạn đã cung cấp)
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
    "pref_karaoke": {"type": "night_club", "keyword": "カラOK"},
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


# ⚙️ Worker cho Phase 1 (NearbySearch)
def fetch_places_for_job(job, location, radius):
    endpoint_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    all_results_for_this_job = []
    
    types_to_search = job['type']
    if not isinstance(types_to_search, list):
        types_to_search = [types_to_search] 

    for place_type in types_to_search:
        params = {
            'location': location,
            'radius': radius,
            'type': place_type, 
            'keyword': job.get('keyword', ''),
            'language': 'ja',
            'key': API_KEY
        }
        page_count = 1
        
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
            
    return all_results_for_this_job

# ⚙️ Worker cho Phase 2 (PlaceDetails)
def fetch_place_details_for_id(place_id, fields_string):
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
                return data['result']
        
        print(f"[DetailsWorker LỖI] {place_id}: {response.text}")
        return None
    except Exception as e:
        print(f"[DetailsWorker LỖI KẾT NỐI] {place_id}: {e}")
        return None

# 🏃‍♂️ Hàm Main để điều phối
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

    all_basic_results = {}
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
    
    pool_size_details = 10 
    pool_details = ThreadPool(pool_size_details)
    worker_details = partial(fetch_place_details_for_id, fields_string=fields_to_request_str)
    
    detailed_results_list = pool_details.map(worker_details, unique_place_ids)
    
    pool_details.close()
    pool_details.join()

    print(f"--- PHASE 2: Hoàn thành. ---")

    # === GỘP KẾT QUẢ CUỐI CÙNG ===
    final_merged_list = []
    details_map = {res['place_id']: res for res in detailed_results_list if res and 'place_id' in res}
    
    for basic_place in unique_basic_results:
        place_id = basic_place['place_id']
        if place_id in details_map:
            basic_place.update(details_map[place_id])
            final_merged_list.append(basic_place)
        else:
            basic_place['details_fetch_failed'] = True 
            final_merged_list.append(basic_place)
            
    print(f"\nĐã gộp thành công {len(final_merged_list)} địa điểm.")
    
    return final_merged_list, logic_filters

# 🌟 HÀM MỚI ĐỂ GỌI TỪ BÊN NGOÀI 🌟
def run_search_and_save(user_choices, user_location, user_radius):
    """
    Hàm chính để chạy toàn bộ quy trình: tìm kiếm, làm giàu dữ liệu, lọc và lưu file.
    Trả về đường dẫn file đã lưu (string) nếu thành công, hoặc None nếu thất bại.
    """
    
    print(f"--- Bắt đầu quy trình với {len(user_choices)} sở thích ---")
    start_time = time.time()
    
    # Chạy hàm chính để lấy TẤT CẢ data (đã gộp)
    full_data_places, filters_to_apply = find_and_enrich_places(
        user_choices, 
        user_location, 
        user_radius, 
        FIELDS_STRING
    )
    
    end_time = time.time()
    print(f"\n--- Tổng thời gian API (cả 2 phase): {end_time - start_time:.2f} giây ---")
    print(f"Các bộ lọc logic cần áp dụng: {filters_to_apply}")
    
    # --- BƯỚC 2: LỌC KẾT QUẢ CUỐI CÙNG ---
    
    print(f"Đang lọc {len(full_data_places)} kết quả để chỉ giữ lại các trường mong muốn...")
    minimal_results_list = []
    
    if full_data_places:
        for place in full_data_places:
            minimal_place = {}

            minimal_place['place_id'] = place.get('place_id')

            if 'geometry' in place and 'location' in place['geometry']:
                minimal_place['location'] = place['geometry']['location']

            minimal_place['types'] = place.get('types', [])
            minimal_place['rating'] = place.get('rating')
            minimal_place['user_ratings_total'] = place.get('user_ratings_total')
            minimal_place['price_level'] = place.get('price_level')

            if 'opening_hours' in place and 'weekday_text' in place['opening_hours']:
                minimal_place['weekday_text'] = place['opening_hours']['weekday_text']

            if 'photos' in place and place['photos']:
                minimal_place['photo_references'] = [
                    photo.get('photo_reference') for photo in place['photos'] 
                    if photo.get('photo_reference')
                ]

            if 'reviews' in place and place['reviews']:
                minimal_place['review_texts'] = [
                    review.get('text') for review in place['reviews'] 
                    if review.get('text')
                ]
            
            minimal_results_list.append(minimal_place)
    
    # --- PHẦN LƯU FILE ---
    if minimal_results_list:
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        safe_prefs = "_".join(user_choices)
        FILENAME = f"MinimalSearch_{safe_prefs}_{timestamp}.json"
        
        # Sử dụng OUTPUT_DIR đã định nghĩa ở trên
        OUTPUT_FILENAME = os.path.join(OUTPUT_DIR, FILENAME) 

        print(f"\nĐang lưu {len(minimal_results_list)} kết quả (đã lọc) vào: {OUTPUT_FILENAME}...")
        
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True) # Tự động tạo thư mục nếu chưa có
            with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(minimal_results_list, f, indent=4, ensure_ascii=False)
            print("Đã lưu file thành công!")
            
            # Trả về đường dẫn file đã lưu
            return OUTPUT_FILENAME
        
        except Exception as e:
            print(f"LỖI khi lưu file: {e}")
            return None # Trả về None nếu lưu lỗi
            
    else:
        print("\nKhông có kết quả nào để lưu.")
        return None # Trả về None nếu không có kết quả


# 🏁 BƯỚC CUỐI: Chạy thử (Chỉ khi chạy trực tiếp file này)
if __name__ == "__main__":
    
    print("--- CHẠY TEST (standalone) ---")
    
    # Giá trị mặc định để test
    DEFAULT_LOCATION = "34.6872571,135.5258546" # Vị trí hardcode cũ
    DEFAULT_RADIUS = 30000                     # Bán kính hardcode cũ
    DEFAULT_CHOICES = ['pref_ramen', 'pref_park', 'pref_museum_art']
    
    # Gọi hàm chính
    saved_file_path = run_search_and_save(
        DEFAULT_CHOICES, 
        DEFAULT_LOCATION, 
        DEFAULT_RADIUS
    )
    
    if saved_file_path:
        print(f"\n--- TEST HOÀN THÀNH. File đã lưu tại: {saved_file_path} ---")
    else:
        print("\n--- TEST HOÀN THÀNH. Không có file nào được tạo. ---")