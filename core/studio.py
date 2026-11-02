"""Lộ trình + tài chính studio. Mọi con số do anh nhập; web chỉ tính toán, không tự đặt số liệu thị trường."""
from __future__ import annotations

STUDIO_AREAS = [
    "Pháp lý & giấy phép", "Mặt bằng", "Tài chính", "Thiết bị", "Nhân sự",
    "Thương hiệu & marketing", "Bán hàng & chăm sóc khách", "Phần mềm quản lý",
]

# Checklist khởi đầu (việc cần làm, KHÔNG kèm số liệu/chi phí). Quý tương đối so với ngày khai trương.
STUDIO_CHECKLIST = [
    ("Q1", "Pháp lý & giấy phép", "Chọn loại hình đăng ký (hộ kinh doanh / công ty) — hỏi tư vấn kế toán/pháp lý"),
    ("Q1", "Tài chính", "Chốt tổng vốn & quỹ dự phòng, lập dòng tiền 12 tháng"),
    ("Q1", "Tài chính", "Tính điểm hoà vốn với giá thuê thật (trang Studio → Tài chính)"),
    ("Q1", "Mặt bằng", "Lập tiêu chí mặt bằng 70–100 m² (vị trí, trần, sàn chịu lực, điện, chỗ để xe)"),
    ("Q1", "Mặt bằng", "Khảo sát ít nhất 3 mặt bằng, ghi giá thuê thật"),
    ("Q1", "Thương hiệu & marketing", "Chốt định vị & tên studio, bảng giá dự kiến"),
    ("Q2", "Mặt bằng", "Đàm phán & ký hợp đồng thuê (thời hạn, tăng giá, thời gian miễn tiền thuê sửa chữa)"),
    ("Q2", "Pháp lý & giấy phép", "Đăng ký kinh doanh, mã số thuế, tài khoản ngân hàng"),
    ("Q2", "Pháp lý & giấy phép", "Kiểm tra yêu cầu PCCC & điều kiện kinh doanh thể thao tại địa phương"),
    ("Q2", "Thiết bị", "Lên danh sách thiết bị ưu tiên theo chương trình tập, xin ≥ 2 báo giá"),
    ("Q2", "Mặt bằng", "Thiết kế bố trí mặt bằng & thi công cải tạo"),
    ("Q2", "Phần mềm quản lý", "Chọn phần mềm quản lý hội viên / đặt lịch / thanh toán"),
    ("Q3", "Thiết bị", "Đặt mua & lắp đặt thiết bị"),
    ("Q3", "Nhân sự", "Mô tả công việc & quy trình tuyển (nếu cần thêm HLV/lễ tân)"),
    ("Q3", "Nhân sự", "Đào tạo & chuẩn hoá quy trình cho nhân sự"),
    ("Q3", "Bán hàng & chăm sóc khách", "Viết kịch bản tư vấn & quy trình chốt gói"),
    ("Q3", "Bán hàng & chăm sóc khách", "Quy trình onboarding, đo InBody, chăm sóc & gia hạn"),
    ("Q3", "Thương hiệu & marketing", "Bộ nhận diện (logo, màu, biển hiệu), fanpage, Google Maps"),
    ("Q4", "Thương hiệu & marketing", "Chiến dịch trước khai trương (danh sách chờ, ưu đãi sáng lập)"),
    ("Q4", "Bán hàng & chăm sóc khách", "Bán trước gói cho khách đầu tiên"),
    ("Q4", "Phần mềm quản lý", "Nhập dữ liệu, chạy thử thanh toán & đặt lịch"),
    ("Q4", "Pháp lý & giấy phép", "Hoàn tất hồ sơ, hợp đồng mẫu với hội viên, bảo hiểm"),
    ("Q4", "Thương hiệu & marketing", "Sự kiện khai trương"),
]

BUDGET_CATEGORIES = ["Mặt bằng & cọc", "Cải tạo / thi công", "Thiết bị", "Pháp lý & giấy phép",
                     "Marketing trước khai trương", "Phần mềm & công nghệ", "Nhân sự & đào tạo", "Khác"]


def breakeven(fixed_month: float, price_per_client: float, variable_per_client: float) -> float | None:
    """Số khách/tháng cần để hoà vốn = chi phí cố định / (doanh thu - chi phí biến đổi mỗi khách)."""
    margin = price_per_client - variable_per_client
    if margin <= 0:
        return None
    return fixed_month / margin


def monthly_kpis(row: dict) -> dict:
    rev = float(row.get("revenue") or 0)
    cost = float(row.get("cost") or 0)
    clients = float(row.get("clients") or 0)
    due = float(row.get("due_renew") or 0)
    renewed = float(row.get("renewed") or 0)
    new = float(row.get("new_clients") or 0)
    mkt = float(row.get("marketing") or 0)
    return {
        "profit": rev - cost,
        "margin": (rev - cost) / rev if rev else None,
        "renew_rate": renewed / due if due else None,
        "cost_per_client": cost / clients if clients else None,
        "cac": mkt / new if new else None,
        "rev_per_client": rev / clients if clients else None,
    }
