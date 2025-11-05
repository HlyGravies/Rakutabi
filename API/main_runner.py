# Đây là file main_runner.py
# Đảm bảo file này nằm CÙNG THƯ MỤC với file api_fetcher.py

import api_fetcher  # Import file trên
import time

print("--- BẮT ĐẦU CHƯƠNG TRÌNH CHÍNH (main_runner.py) ---")

# 1. Cung cấp các giá trị MỚI của bạn ở đây
NEW_USER_LOCATION = "35.689487, 139.691711"  # Ví dụ: Ga Tokyo
NEW_USER_RADIUS = 10000                      # Ví dụ: Bán kính 10km
USER_PREFERENCES = ['pref_cafe', 'pref_sento', 'pref_bookstore']

print(f"Đang chuẩn bị tìm kiếm cho: {USER_PREFERENCES}")
print(f"Vị trí: {NEW_USER_LOCATION}, Bán kính: {NEW_USER_RADIUS}m")

start_total_time = time.time()

try:
    # 2. Gọi hàm từ file api_fetcher và truyền tham số mới
    # Hàm này sẽ chạy và trả về đường dẫn file (hoặc None)
    generated_filepath = api_fetcher.run_search_and_save(
        USER_PREFERENCES,
        NEW_USER_LOCATION,
        NEW_USER_RADIUS
    )

    end_total_time = time.time()
    print(f"\n--- TỔNG THỜI GIAN CHẠY: {end_total_time - start_total_time:.2f} giây ---")

    # 3. Lưu lại biến OUTPUT_FILENAME (giờ là 'generated_filepath')
    if generated_filepath:
        print("\n✅ HOÀN THÀNH!")
        print(f"Biến chứa đường dẫn file là 'generated_filepath'")
        print(f"Đường dẫn file đã lưu: {generated_filepath}")
        
        # Bạn có thể làm bất cứ điều gì bạn muốn với biến này
        # Ví dụ: đọc lại file
        # with open(generated_filepath, 'r', encoding='utf-8') as f:
        #     data = json.load(f)
        #     print(f"Đã đọc lại file, có {len(data)} địa điểm.")

    else:
        print("\n❌ KHÔNG THÀNH CÔNG.")
        print("Quy trình chạy xong nhưng không có file nào được tạo (có thể do không tìm thấy kết quả).")

except Exception as e:
    print(f"\n🔥🔥🔥 ĐÃ XẢY RA LỖI NGHIÊM TRỌNG: {e}")