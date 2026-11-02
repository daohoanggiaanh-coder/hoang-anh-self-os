# Hoàng Anh · Self OS

Web app cá nhân để học, làm, theo dõi và phát triển bản thân mỗi ngày.
Streamlit + Google Sheets (qua Apps Script) + Google Calendar.

## Đã có (phiên bản 0.1.0)
- Đăng nhập 1 tài khoản, ghi nhớ đăng nhập (cookie 180 ngày + dự phòng `?k=`).
- Giao diện đen – vàng đồng / kem – vàng đồng, font Be Vietnam Pro, gọn trên điện thoại, có icon + manifest.
- **Hôm nay của tôi**: lịch hôm nay, giờ trống còn lại, khoảng trống kế tiếp, nhắc nhẹ.
- **Lịch & giờ trống**: lịch cố định, ca PT đọc từ lịch Google "PT" (+15' đi lại), việc phát sinh,
  tìm giờ trống ≥ 30', đề xuất xếp khối theo năng lượng (đệm 15'), Nhận / Đổi / Bỏ, cảnh báo trùng giờ, thiếu ngủ, quá tải.
- **Cài đặt**: giờ năng lượng, quy tắc xếp, ngưỡng nhắc, tên lịch Google.

## Chạy thử trên máy
```bash
pip install -r requirements.txt
# tạo .streamlit/secrets.toml với: APP_PASSWORD = "..."
streamlit run app.py
python -m pytest -q        # chạy test tự động
```
Không có `APPS_SCRIPT_URL` → dữ liệu lưu tạm ở thư mục `data/` (chỉ để thử).

---
## Cài đặt thật (anh làm 1 lần, ~20 phút)

### Bước 1 — Lịch Google "PT"
calendar.google.com (trên máy tính) → cạnh **Lịch khác** bấm **+** → **Tạo lịch mới** → tên `PT` → **Tạo lịch**.
Từ nay ca dạy nhập vào lịch này.

### Bước 2 — Google Sheet + Apps Script
1. Tạo Google Sheet mới, đặt tên **Self OS – Data**.
2. **Tiện ích mở rộng → Apps Script**. Xoá code mẫu, dán toàn bộ `apps_script/Code.gs`. Bấm 💾.
3. **Cài đặt dự án** (bánh răng bên trái) → **Thuộc tính tập lệnh** → **Thêm thuộc tính**:
   `TOKEN` = một chuỗi bí mật dài (VD 32 ký tự ngẫu nhiên). Lưu.
4. Quay lại trình soạn thảo, chọn hàm **setup** → **Chạy** → cấp quyền (Google sẽ cảnh báo
   "ứng dụng chưa xác minh" vì đây là script của chính anh → **Nâng cao → Đi tới… → Cho phép**).
   Nhật ký phải hiện "Đã thấy lịch PT".
5. **Triển khai → Tùy chọn triển khai mới** → loại **Ứng dụng web**:
   *Thực thi với tư cách*: **Tôi** · *Người có quyền truy cập*: **Bất kỳ ai** → **Triển khai** → copy **URL ứng dụng web**.
   (Ai có URL mà không có TOKEN thì không đọc/ghi được.)
6. Sửa Code.gs sau này: **Triển khai → Quản lý triển khai → ✎ → Phiên bản: Mới** (giữ nguyên URL).

### Bước 3 — GitHub + Streamlit Community Cloud
1. Đẩy thư mục này lên GitHub (repo mới, VD `hoang-anh-self-os`). Không đẩy `.streamlit/secrets.toml` (đã có trong .gitignore).
2. share.streamlit.io → **Create app** → chọn repo, nhánh `main`, file `app.py`.
3. **Advanced settings → Secrets**, dán:
   ```toml
   APP_PASSWORD = "mật khẩu anh chọn"
   APPS_SCRIPT_URL = "https://script.google.com/macros/s/.../exec"
   APPS_SCRIPT_TOKEN = "đúng chuỗi TOKEN ở Bước 2"
   ```
4. Deploy. Vào **Cài đặt → Kiểm tra kết nối** để chắc chắn Sheets + lịch PT đã nối.

### Bước 4 — Cài như app trên điện thoại
- iPhone (Safari): mở web → đăng nhập (tick "Ghi nhớ") → nút **Chia sẻ** → **Thêm vào MH chính**.
- Android (Chrome): ⋮ → **Thêm vào màn hình chính / Cài đặt ứng dụng**.
Nếu lần sau mở lại bị hỏi mật khẩu: mở web bằng địa chỉ có `?k=…` (hiện sau khi đăng nhập) rồi thêm vào màn hình chính lại.

## Quy ước
- Mỗi lần sửa: tăng `core/version.py` và ghi `CHANGELOG.md`; chạy `python -m pytest -q` trước khi đẩy.
- Dữ liệu: mỗi tab Sheet = 1 bảng (`key | ts | deleted | data`), chỉ ghi nối dòng; bản mới nhất theo key là bản đang dùng.
