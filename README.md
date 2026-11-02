# Công cụ dịch Trung - Việt cho Windows

Tiện ích Windows mở một bảng dịch luôn hiển thị ba dòng thông tin:

- **Chữ Hán** được bôi đen.
- **Pinyin có dấu thanh** được tạo cục bộ.
- **Nghĩa tiếng Việt** được dịch trực tuyến.

Bôi đen chữ Trung bằng chuột; khi thả chuột, ứng dụng tự lấy vùng chọn và cập nhật bảng, không cần nhấn phím tắt dịch. Bảng sẽ giữ kết quả gần nhất cho tới khi có vùng chọn mới. Ứng dụng không OCR hay theo dõi vị trí con trỏ. Nhấn `Ctrl+Shift+Q` hoặc đóng cửa sổ để thoát.

Giao diện lấy cảm hứng từ giấy xuyến chỉ và thư pháp Trung Hoa, với nền màu ngà, mực xanh đậm, triện son và các thẻ thông tin riêng cho chữ Hán, pinyin, nghĩa.

## Cài đặt và chạy

Cần Python 3.10 trở lên. Mở PowerShell tại thư mục dự án và chạy:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python translator.py
```

Có thể kéo bảng dịch đến vị trí thuận tiện.

## Dịch vụ dịch và riêng tư

Văn bản bôi đen được gửi tới MyMemory (`api.mymemory.translated.net`) để dịch từ tiếng Trung giản thể sang tiếng Việt; cần kết nối Internet. Dịch vụ miễn phí có thể giới hạn lưu lượng hoặc tạm thời không khả dụng. Không dùng với văn bản nhạy cảm.

Mỗi yêu cầu giới hạn 450 ký tự. Ứng dụng dùng `Ctrl+C` nội bộ để lấy vùng chọn sau khi thả chuột, rồi khôi phục nội dung văn bản clipboard trước đó. Cần ứng dụng đang dùng hỗ trợ sao chép vùng chọn.
