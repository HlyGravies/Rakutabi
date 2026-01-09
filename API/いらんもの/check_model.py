import google.generativeai as genai

# Key của ông
api_key = "AIzaSyCHAV26v44x6YqeuclZZ1I4RquRr9Nk6bQ"
genai.configure(api_key=api_key)

print("--- DANH SÁCH MODEL KHẢ DỤNG ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Lỗi: {e}")