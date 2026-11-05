# Nhật ký phiên bản

## 0.4.0 — 05/11/2026
- Lịch làm tuần: giờ làm thường lệ 7h–10h và 17h–21h (loại “Giờ làm Atlas” 🕘), bấm chọn ngày nghỉ cho từng tuần, lưu làm mặc định.
- Ca khách sớm/muộn hơn giờ làm lấy từ Google Calendar, nối liền với giờ làm khi tính đi lại; dạy trong giờ làm không báo trùng.
- ＋ Thêm việc 4 bước (Việc gì → Loại → Bao lâu → Khi nào), có tuỳ chọn lặp lại mỗi tuần; có ở trang Hôm nay và Lịch.
- Việc lặp lại hằng tuần (bảng quản lý trong “Việc cần xếp”), tự đưa vào Đề xuất xếp lịch.
- Loại mới 🎬 Quay / dựng video. Thêm sẵn series 84 ngày (09/11/2026–31/01/2027): quay 2 buổi × 90' và dựng 2 buổi × 60' mỗi tuần.
- Giờ làm việc trong tuần tính theo hợp các khoảng (không cộng trùng).

## 0.3.0 — 03/11/2026
- Phân loại & màu: 12 loại việc có màu + biểu tượng riêng (Dạy PT · Khách riêng, Dạy PT · Atlas, Quản lý Atlas, Học, Tự tập, Burpee…), chú thích màu.
- Bản đồ màu cả tuần (5h–23h) + tổng giờ theo loại.
- Đọc lịch Atlas do lễ tân nhập (pigngo2101@gmail.com), chỉ lấy ca màu đỏ (= ca của anh).
- Quy tắc phân loại theo từ khoá / màu Google, sửa được trong Cài đặt; chỉ loại PT/Atlas được cộng giờ đi lại.
- Khối do web tạo trên Google Calendar được tô màu theo loại.

## 0.2.5 — 03/11/2026
- Đọc cả lịch chính + lịch PT trong 1 lần gọi (bật/tắt trong Cài đặt); bỏ các khối do Self OS tạo để không tính trùng.

## 0.2.4 — 03/11/2026
- Khôi phục đăng nhập từ cookie bằng ô nhập ẩn (iframe Streamlit không được phép chuyển trang).

## 0.2.3 — 03/11/2026
- Ghi nhớ đăng nhập trên Streamlit Cloud: Cloud không chuyển cookie cho app → trang đăng nhập đọc cookie bằng JS và tự nạp lại với mã ghi nhớ.

## 0.2.2 — 03/11/2026
- Sửa lỗi AttributeError `read_many` sau khi cập nhật: kết nối lưu trữ được tạo lại theo từng phiên bản code.

## 0.2.1 — 03/11/2026
- Tăng tốc: đọc gộp mọi bảng trong 1 lần gọi Apps Script (`read_many`), ghi xong cập nhật bộ đệm tại chỗ thay vì đọc lại.
  Trước đây mỗi trang gọi Google ~20 lần nối tiếp (rất chậm trên Streamlit Cloud).
- Test: giới hạn số lần đọc backend mỗi trang.

## 0.2.0 — 02/11/2026
- Mục tiêu Năm → Quý → Tuần (OKR) + lịch sử Top 3.
- Hôm nay: Top 3, thói quen, giờ học (đánh dấu “Đã học” từ khối lịch), động lực, tổng kết 3 câu, nhắc nhẹ.
- Thói quen: chuỗi ngày (không phạt ngày chưa hết), kỷ lục, biểu đồ 4 tuần, lưới 28 ngày.
- Kỹ năng: giờ/tuần, tài liệu, nhật ký học, bài thực hành; trang Lịch tự chèn giờ học còn thiếu.
- Vẻ ngoài: checklist da/tóc/tư thế/trang phục, số đo (cân, % mỡ, eo), ảnh tiến độ 4 tuần (so trước/sau), lịch cắt tóc, tủ đồ.
- Studio: lộ trình theo quý (8 hạng mục), ngân sách dự kiến/thực chi, điểm hoà vốn, bảng điều hành sau khai trương.
- Tổng kết tuần/tháng: % Top 3, thói quen, giờ học, studio + nhận xét & đề xuất theo quy tắc.
- Động lực: điểm (chỉ cộng), 13 cấp độ, 10 huy hiệu.
- Sửa: bảng nhập liệu giữ nguyên trường ẩn khi sửa dòng; biểu đồ sắp đúng thứ tự ngày.
- 40 test tự động.

## 0.1.0 — 02/11/2026
- Khung app: đăng nhập 1 tài khoản + ghi nhớ, giao diện đen – vàng đồng (sáng/tối), font Be Vietnam Pro, icon + manifest.
- Lưu trữ Google Sheets qua Apps Script (ghi nối dòng, bản mới nhất theo key); chế độ lưu local để thử.
- Đọc lịch Google "PT"; tạo sự kiện riêng tư khi nhận đề xuất.
- Trang Hôm nay, Lịch & giờ trống (tìm giờ trống, đề xuất time-blocking, Nhận/Đổi/Bỏ, cảnh báo), Cài đặt.
- 25 test tự động (bộ máy lịch, lưu trữ, giao diện).
