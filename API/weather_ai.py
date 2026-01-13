import requests
import json
import joblib
import numpy as np
import os
import logging
from datetime import datetime, timezone, timedelta

# --- 1. IMPORT TENSORFLOW ---
try:
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
    from tensorflow.keras.models import load_model
except ImportError:
    logging.warning("⚠️ Chưa cài thư viện 'tensorflow'.")
    load_model = None

# ===================== CẤU HÌNH =====================
# API Keys từ code gốc của bạn
GOOGLE_API_KEY = "AIzaSyDvvaIASfr2Hzi3oUx5RFi6wT0bpKsCLRU"
WEATHER_API_KEY = "c2127cc17736f9f41cdfbce58c099e6f"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Biến toàn cục để load model 1 lần
model = None
scaler = None
mlb_clothes = None
mlb_health = None

# ===================== LOAD MODEL =====================
def load_ai_models():
    global model, scaler, mlb_clothes, mlb_health
    if load_model is None: return

    try:
        # Đường dẫn tuyệt đối để tránh lỗi trong Flask
        model_path = os.path.join(BASE_DIR, "model_clothes_health.h5")
        scaler_path = os.path.join(BASE_DIR, "scaler.pkl")
        clothes_path = os.path.join(BASE_DIR, "mlb_clothes.pkl")
        health_path = os.path.join(BASE_DIR, "mlb_health.pkl")

        if os.path.exists(model_path):
            model = load_model(model_path)
            scaler = joblib.load(scaler_path)
            mlb_clothes = joblib.load(clothes_path)
            mlb_health = joblib.load(health_path)
            print("✅ Đã load Model AI thành công (Logic gốc)!")
        else:
            print("⚠️ Thiếu file model (.h5/.pkl).")
    except Exception as e:
        print(f"❌ Lỗi load model: {e}")

load_ai_models()

# ===================== LOGIC CỐT LÕI (GIỮ NGUYÊN TỪ CODE BẠN GỬI) =====================

def get_forecast_weather_raw(lat, lon, hours_ahead=10):
    # Lấy dữ liệu thô từ OpenWeatherMap
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=ja"
    response = requests.get(url)
    data = response.json()
    if "list" not in data: return [], []
    
    forecast_list = data["list"][:hours_ahead]
    weather_features_list = []
    weather_info_list = []
    
    for hour in forecast_list:
        temp = hour["main"]["temp"]
        feels_like = hour["main"]["feels_like"]
        humidity = hour["main"]["humidity"] / 100.0
        wind_speed = hour["wind"]["speed"] * 3.6  # m/s -> km/h
        wind_deg = hour["wind"].get("deg", 0)
        visibility = hour.get("visibility", 10000) / 1000.0  # m -> km
        cloud_cover = hour["clouds"]["all"] / 100.0
        weather_condition = hour["weather"][0]["main"].lower()
        
        # Timezone +9 (Japan)
        dt = datetime.fromtimestamp(hour["dt"], tz=timezone.utc) + timedelta(hours=9)
        hour_label = dt.strftime("%H:%M")

        # Input cho AI (đúng 7 tham số)
        weather_features = np.array([[temp, feels_like, humidity, wind_speed, wind_deg, visibility, cloud_cover]])
        
        # Info để hiển thị & lọc
        weather_info = {
            "dt_object": dt, # Lưu object để tính ngày (Hôm nay/Mai)
            "hour": hour_label,
            "temperature_C": round(temp, 2),
            "feels_like_C": round(feels_like, 2),
            "humidity_percent": round(humidity * 100, 1),
            "wind_speed_kmh": round(wind_speed, 1),
            "weather_condition": weather_condition,
            "icon_code": hour["weather"][0]["icon"], # Thêm để lấy ảnh
            "description": hour["weather"][0]["description"] # Thêm mô tả
        }
        
        weather_features_list.append(weather_features)
        weather_info_list.append(weather_info)
    
    return weather_features_list, weather_info_list

def get_uv_forecast(lat, lon):
    url = f"https://currentuvindex.com/api/v1/uvi?latitude={lat}&longitude={lon}"
    try:
        response = requests.get(url, timeout=5) # Timeout ngắn tránh treo server
        data = response.json()
        if not data.get("ok"): return []
        return data.get("forecast", [])
    except Exception:
        return []

def get_summary_level(temp, weather_condition):
    levels = []
    if temp <= 10: levels.append("cold")
    elif temp >= 28: levels.append("hot")
    if weather_condition in ["rain", "drizzle", "thunderstorm", "snow"]:
        levels.append("rain")
    if not levels: levels.append("normal")
    return levels

def predict_clothes_health(weather_features):
    if model is None: return [], []
    try:
        X_scaled = scaler.transform(weather_features)
        Y_pred = model.predict(X_scaled, verbose=0)
        Y_pred_binary = (Y_pred > 0.5).astype(int)
        
        n_clothes = len(mlb_clothes.classes_)
        clothes_pred = mlb_clothes.inverse_transform(Y_pred_binary[:, :n_clothes])
        health_pred = mlb_health.inverse_transform(Y_pred_binary[:, n_clothes:])
        
        return list(clothes_pred[0]) if clothes_pred else [], list(health_pred[0]) if health_pred else []
    except Exception as e:
        print(f"Prediction Error: {e}")
        return [], []

def filter_clothes_and_health(clothes, health, weather_info):
    condition = weather_info["weather_condition"]
    temp = weather_info["temperature_C"]
    feels_like = weather_info["feels_like_C"]
    humidity = weather_info["humidity_percent"]
    wind_speed = weather_info["wind_speed_kmh"]
    uv_index = weather_info.get("uv_index", 0)
    
    is_rain = condition in ["rain", "drizzle", "thunderstorm", "snow"]
    
    if not is_rain:
        clothes = [c for c in clothes if c not in ["防水シューズ", "傘", "レインコート"]]
    
    health_warnings = []
    if temp < 5: health_warnings.append("風邪のリスク注意")
    if feels_like > 35 or temp >= 35: health_warnings.append("熱中症の危険 – 水分補給を忘れずに")
    if humidity > 80: health_warnings.append("インフルエンザや不快感に注意")
    if wind_speed > 40: health_warnings.append("防風ジャケットをおすすめ")
    if uv_index >= 6: health_warnings.append("紫外線が強い – 日焼け止めや帽子を使用してください")
    
    if not is_rain:
        health = [h for h in health if not any(x in h for x in ["防水シューズ", "傘", "滑り"])]
    
    health_warnings = list(set(health + health_warnings))
    return clothes, health_warnings

# ===================== MAIN HANDLER (GỌI TỪ FLASK) =====================
def get_weather_advice(lat, lon):
    try:
        # 1. Lấy dữ liệu (Mặc định lấy 10 mốc ~ 30 tiếng)
        weather_features_list, weather_info_list = get_forecast_weather_raw(lat, lon, hours_ahead=10)
        uv_forecast = get_uv_forecast(lat, lon)
        
        # 2. Xử lý ngày hiện tại (để gắn nhãn Today/Tomorrow cho UI)
        now_utc = datetime.now(timezone.utc)
        now_jst = now_utc + timedelta(hours=9)
        today_date = now_jst.date()
        tomorrow_date = (now_jst + timedelta(days=1)).date()

        forecasts = []
        
        for i, (weather_features, weather_info) in enumerate(zip(weather_features_list, weather_info_list)):
            # Gắn UV index (Khớp theo index i)
            if i < len(uv_forecast):
                weather_info["uv_index"] = uv_forecast[i].get("uvi", 0)
            else:
                weather_info["uv_index"] = 0

            # Chạy logic AI & Filter gốc
            summary_level = get_summary_level(weather_info["temperature_C"], weather_info["weather_condition"])
            clothes, health = predict_clothes_health(weather_features)
            clothes, health_warnings = filter_clothes_and_health(clothes, health, weather_info)

            # Tạo nhãn ngày cho UI (Thêm phần này để giao diện đẹp)
            item_date = weather_info["dt_object"].date()
            if item_date == today_date: date_label = "今日"
            elif item_date == tomorrow_date: date_label = "明日"
            else: date_label = item_date.strftime("%m/%d")

            # Đóng gói kết quả (Giống JSON mẫu + icon + date_label)
            result = {
                "date_label": date_label, # UI cần
                "icon": f"http://openweathermap.org/img/wn/{weather_info['icon_code']}.png", # UI cần
                "weather_info": {
                    "hour": weather_info["hour"],
                    "temperature_C": weather_info["temperature_C"],
                    "feels_like_C": weather_info["feels_like_C"],
                    "humidity_percent": weather_info["humidity_percent"],
                    "wind_speed_kmh": weather_info["wind_speed_kmh"],
                    "weather_condition": weather_info["weather_condition"],
                    "uv_index": weather_info["uv_index"],
                    "description": weather_info["description"]
                },
                "summary_level": summary_level,
                "clothing_suggestions_jp": clothes,
                "health_warnings_jp": health_warnings
            }
            forecasts.append(result)

        # Trả về format chung để Flask jsonify
        return {
            "success": True,
            "city": "Selected Location", # Tạm thời
            "forecasts": forecasts
        }

    except Exception as e:
        print(f"❌ Error in get_weather_advice: {e}")
        return {"success": False, "error": str(e)}