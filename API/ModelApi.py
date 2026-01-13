import requests
import json
import joblib
import numpy as np
from tensorflow.keras.models import load_model
from datetime import datetime, timezone, timedelta

# ===================== API Keys =====================
GOOGLE_API_KEY = "AIzaSyDvvaIASfr2Hzi3oUx5RFi6wT0bpKsCLRU"
WEATHER_API_KEY = "c2127cc17736f9f41cdfbce58c099e6f"

# ===================== Lấy vị trí hiện tại =====================
def get_current_location():
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
    payload = {"considerIp": True}
    response = requests.post(url, json=payload)
    data = response.json()
    if "location" not in data:
        raise Exception("現在の位置を取得できません")
    return data["location"]["lat"], data["location"]["lng"]

# ===================== Lấy dự báo thời tiết =====================
def get_forecast_weather(lat, lon, hours_ahead=3):
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()
    if "list" not in data:
        raise Exception(f"天気予報データを取得できません: {data}")
    
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
        dt = datetime.fromtimestamp(hour["dt"], tz=timezone.utc) + timedelta(hours=9)
        hour_label = dt.strftime("%H:%M")

        weather_features = np.array([[temp, feels_like, humidity, wind_speed, wind_deg, visibility, cloud_cover]])
        weather_info = {
            "hour": hour_label,
            "temperature_C": round(temp, 2),
            "feels_like_C": round(feels_like, 2),
            "humidity_percent": round(humidity * 100, 1),
            "wind_speed_kmh": round(wind_speed, 1),
            "weather_condition": weather_condition
        }
        
        weather_features_list.append(weather_features)
        weather_info_list.append(weather_info)
    
    return weather_features_list, weather_info_list

# ===================== Lấy dự báo UV theo giờ =====================
def get_uv_forecast(lat, lon):
    url = f"https://currentuvindex.com/api/v1/uvi?latitude={lat}&longitude={lon}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        print("UV API error:", e)
        return []

    if not data.get("ok"):
        print("UV API returned not ok")
        return []

    forecast_list = data.get("forecast", [])
    if not forecast_list:
        print("UV forecast empty, returning empty list")
        return []

    return forecast_list

# ===================== Tạo mức dự báo tổng quan =====================
def get_summary_level(temp, weather_condition):
    levels = []
    if temp <= 10:
        levels.append("cold")
    elif temp >= 28:
        levels.append("hot")
    if weather_condition in ["rain", "drizzle", "thunderstorm", "snow"]:
        levels.append("rain")
    if not levels:
        levels.append("normal")
    return levels

# ===================== Load model AI =====================
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

scaler = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))
mlb_clothes = joblib.load(os.path.join(BASE_DIR, "mlb_clothes.pkl"))
mlb_health = joblib.load(os.path.join(BASE_DIR, "mlb_health.pkl"))
model = load_model(os.path.join(BASE_DIR, "model_clothes_health.h5"))

# ===================== Dự đoán trang phục và sức khỏe =====================
def predict_clothes_health(weather_features):
    X_scaled = scaler.transform(weather_features)
    Y_pred = model.predict(X_scaled)
    Y_pred_binary = (Y_pred > 0.5).astype(int)
    
    n_clothes = len(mlb_clothes.classes_)
    clothes_pred = mlb_clothes.inverse_transform(Y_pred_binary[:, :n_clothes])
    health_pred = mlb_health.inverse_transform(Y_pred_binary[:, n_clothes:])
    
    return list(clothes_pred[0]) if clothes_pred else [], list(health_pred[0]) if health_pred else []

# ===================== Lọc trang phục và nâng cao cảnh báo sức khỏe =====================
def filter_clothes_and_health(clothes, health, weather_info):
    condition = weather_info["weather_condition"]
    temp = weather_info["temperature_C"]
    feels_like = weather_info["feels_like_C"]
    humidity = weather_info["humidity_percent"]
    wind_speed = weather_info["wind_speed_kmh"]
    uv_index = weather_info.get("uv_index", 0)
    
    is_rain = condition in ["rain", "drizzle", "thunderstorm", "snow"]
    
    # Nếu trời khô, loại bỏ trang phục chống mưa
    if not is_rain:
        clothes = [c for c in clothes if c not in ["防水シューズ", "傘", "レインコート"]]
    
    # Cảnh báo sức khỏe nâng cao
    health_warnings = []
    if temp < 5:
        health_warnings.append("風邪のリスク注意")
    if feels_like > 35 or temp >= 35:
        health_warnings.append("熱中症の危険 – 水分補給を忘れずに")
    if humidity > 80:
        health_warnings.append("インフルエンザや不快感に注意")
    if wind_speed > 40:
        health_warnings.append("防風ジャケットをおすすめ")
    if uv_index >= 6:
        health_warnings.append("紫外線が強い – 日焼け止めや帽子を使用してください")
    
    # Nếu trời khô, loại bỏ cảnh báo liên quan mưa
    if not is_rain:
        health = [h for h in health if not any(x in h for x in ["防水シューズ", "傘", "滑り"])]
    
    health_warnings = list(set(health + health_warnings))
    
    return clothes, health_warnings

# ===================== Chạy chương trình chính =====================
if __name__ == "__main__":
    lat, lon = get_current_location()
    
    weather_features_list, weather_info_list = get_forecast_weather(lat, lon, hours_ahead=3)
    uv_forecast = get_uv_forecast(lat, lon)

    results = []
    for i, (weather_features, weather_info) in enumerate(zip(weather_features_list, weather_info_list)):
        # Gắn UV index
        if i < len(uv_forecast):
            weather_info["uv_index"] = uv_forecast[i]["uvi"]
        else:
            weather_info["uv_index"] = 0

        summary_level = get_summary_level(weather_info["temperature_C"], weather_info["weather_condition"])
        clothes, health = predict_clothes_health(weather_features)
        clothes, health_warnings = filter_clothes_and_health(clothes, health, weather_info)

        result = {
            "weather_info": weather_info,
            "summary_level": summary_level,
            "clothing_suggestions_jp": clothes,
            "health_warnings_jp": health_warnings
        }
        results.append(result)

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("服装予測と高度な健康・UV警告を result.json に保存しました")
