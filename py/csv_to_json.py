import csv
import json

# --- THAY ĐỔI CÁC TÊN TỆP Ở ĐÂY ---
tsv_file_path = r"F:\PythonProject\Rakutabi\py\0-all.tsv"  # Tên tệp TSV đầu vào của bạn
json_file_path = 'output.json' # Tên tệp JSON bạn muốn tạo

# Danh sách để lưu trữ tất cả các đối tượng (dòng)
data = []

try:
    # Mở tệp TSV để đọc với encoding='utf-8' để xử lý ký tự tiếng Nhật
    with open(tsv_file_path, mode='r', encoding='utf-8') as tsv_file:
        
        # Sử dụng csv.reader với dấu phân cách là tab
        tsv_reader = csv.reader(tsv_file, delimiter='\t')
        
        # Đọc dòng đầu tiên làm tiêu đề (tên các cột)
        headers = next(tsv_reader)
        
        # Lặp qua từng dòng còn lại trong tệp TSV
        for row in tsv_reader:
            # Tạo một dictionary bằng cách ghép tiêu đề với dữ liệu của dòng tương ứng
            row_dict = dict(zip(headers, row))
            data.append(row_dict)

    # Mở tệp JSON để ghi với encoding='utf-8'
    with open(json_file_path, mode='w', encoding='utf-8') as json_file:
        # Ghi danh sách các dictionary vào tệp JSON
        # ensure_ascii=False để giữ nguyên các ký tự tiếng Nhật
        # indent=4 để định dạng tệp JSON cho dễ đọc
        json.dump(data, json_file, ensure_ascii=False, indent=4)
        
    print(f"Chuyển đổi thành công! Dữ liệu đã được lưu vào tệp '{json_file_path}'")

except FileNotFoundError:
    print(f"Lỗi: Không tìm thấy tệp '{tsv_file_path}'. Hãy chắc chắn rằng tệp nằm đúng vị trí.")
except Exception as e:
    print(f"Đã xảy ra lỗi: {e}")