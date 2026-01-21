import os
import json
import google.generativeai as genai
from pathlib import Path
import logging

# --- Cấu hình logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. CONFIG KEY ---
try:
    # ⚠️ THAY KEY CỦA BẠN VÀO ĐÂY
    api_key = "AIzaSyCPCZMZ1_NN5nAlU8YGL60pv5j4bzr8lCE"
    
    if api_key: 
        genai.configure(api_key=api_key)
        logging.info("Đã cấu hình Gemini API Key.")
    else:
        raise EnvironmentError("GEMINI_API_KEY chưa được đặt.")
except Exception as e:
    logging.error(f"Lỗi cấu hình: {e}")

# --- 2. SƠ CHẾ DỮ LIỆU ---
def preprocess_data_for_gemini(original_data: list) -> list:
    lightweight_data = []
    for place in original_data:
        if not isinstance(place, dict): continue
        light_place = {
            "place_id": place.get("place_id"),
            "name": place.get("name"), 
            "location": place.get("location"),
            "types": place.get("types"),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("user_ratings_total"),
            "price_level": place.get("price_level")
        }
        lightweight_data.append(light_place)
    return lightweight_data

# --- 3. TẠO MAP TRA CỨU ---
def create_lookup_maps(original_data: list) -> (dict, dict):
    photo_lookup = {}
    review_lookup = {}
    for place in original_data:
        if not isinstance(place, dict): continue
        place_id = place.get("place_id")
        if place_id:
            photo_lookup[place_id] = place.get("photo_references", [])
            review_lookup[place_id] = place.get("review_texts", [])
    return photo_lookup, review_lookup

# --- 4. LÀM GIÀU DỮ LIỆU ---
def enrich_plans_with_details(plans: list, photo_lookup: dict, review_lookup: dict) -> list:
    for plan in plans:
        if "waypoints" not in plan or not isinstance(plan["waypoints"], list): continue
        for waypoint in plan["waypoints"]:
            place_id = waypoint.get("place_id")
            if place_id:
                waypoint["photo_references"] = photo_lookup.get(place_id, [])
                waypoint["review_texts"] = review_lookup.get(place_id, [])
    return plans

# --- 5. HÀM CHÍNH (TỐI ƯU HÓA TỐC ĐỘ) ---
def create_trip_plan_from_file(places_input_filepath: str, user_location_dict: dict, requested_duration_text: str):
    try:
        input_path = Path(places_input_filepath)
        if not input_path.exists(): return None

        # Output path
        output_dir = Path("json/GeminiAPIResponse")
        output_file_name = f"{input_path.stem}_geminiAPI_Enriched.json"
        output_file_path = output_dir / output_file_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Đọc dữ liệu
        with open(input_path, "r", encoding="utf-8") as f:
            original_places_data = json.load(f)
        
        if not original_places_data: return None

        # Sơ chế
        lightweight_data = preprocess_data_for_gemini(original_places_data)
        photo_lookup, review_lookup = create_lookup_maps(original_places_data)

        prompt = f"""
            あなたはプロの旅行ガイドです。
            ユーザーの現在地: {user_location_dict}
            希望所要時間: "{requested_duration_text}"
            
            以下の提供された場所データ（JSON）のみを使用して、最適な観光プランを **1つだけ** 作成してください。

            【要件】
            1. 移動順序が論理的で効率的であること。
            2. 各場所の `place_id` を必ず含めること。
            3. `estimated_duration_hours` は数値で出力すること（例: 4.5）。
            4. 出力言語は **日本語** です。
            5. `region_name` には、このプランの全スポットが含まれる「都市名」または「主要エリア名」を記入してください（例：新宿、大阪市、京都・嵐山）。
            6. `plan_title`、`theme`、`activity`、`info`、`summary`は魅力的で自然な日本語で記述してください。
            """

        single_plan_schema = {
            "type": "object",
            "properties": {
                # ▼▼▼ ここを追加 ▼▼▼
                "region_name": {
                    "type": "string", 
                    "description": "プラン全体が含まれる主要な都市名や地域名（例: 新宿区、大阪市、嵐山エリア）"
                },
                # ▲▲▲ ここまで ▲▲▲
                
                "plan_title": {"type": "string"},
                "theme": {"type": "string"},
                "estimated_duration_hours": {"type": "number"},
                "waypoints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "place_id": {"type": "string"}, 
                            "order": {"type": "integer"},
                            "name": {"type": "string"},
                            "activity": {"type": "string"},
                            "location": {
                                "type": "object",
                                "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}}
                            },
                            "info": {"type": "string"},
                            "transport_mode": {"type": "string"}
                        },
                        "required": ["place_id", "order", "name", "location", "info"]
                    }
                },
                "summary": {"type": "string"}
            },
            # ▼▼▼ requiredにも region_name を追加 ▼▼▼
            "required": ["region_name", "plan_title", "waypoints", "estimated_duration_hours"]
        }
        
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "array", # Vẫn trả về Array để Frontend dễ loop
                "items": single_plan_schema 
            }
        }

        # --- GỌI API (DÙNG FLASH 1.5 CHO NHANH) ---
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", # Flash cho tốc độ cao
            generation_config=generation_config
        )

        response = model.generate_content(
            f"{prompt}\n\nDữ liệu:\n{json.dumps(lightweight_data, ensure_ascii=False)}",
            request_options={'timeout': 60} 
        )

        plans_from_gemini = json.loads(response.text)

        # Nếu model trả về 1 object thay vì list, ta tự đóng gói vào list
        if isinstance(plans_from_gemini, dict):
            plans_from_gemini = [plans_from_gemini]
        
        # Chỉ lấy 1 plan đầu tiên (Double check)
        plans_from_gemini = plans_from_gemini[:1]

        # Làm giàu dữ liệu
        enriched_plans = enrich_plans_with_details(plans_from_gemini, photo_lookup, review_lookup)

        # Lưu file
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(enriched_plans, f, ensure_ascii=False, indent=4)

        return str(output_file_path.absolute())

    except Exception as e:
        logging.error(f"Lỗi: {e}")
        return None