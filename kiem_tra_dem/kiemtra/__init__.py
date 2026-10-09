"""Gói kiemtra: chấm điểm file DEM .tif theo bộ tiêu chí C1-C8.

Các module:
    cau_hinh.py     cấu hình mặc định, đọc file .yaml, phiếu bàn giao
    doc_du_lieu.py  đọc .tif, bảng điểm, ranh giới; lấy cao độ DEM tại điểm
    do_lech.py      ME, SD, MAE, RMSE, LE90, bootstrap, Spearman
    tieu_chi.py     điểm C1-C8
    xep_loai.py     tổng điểm, quy đổi, xếp loại, điều kiện chặn
    bao_cao.py      in kết quả ra màn hình, ghi file
"""

PHIEN_BAN = "1.1.0"


class LoiDauVao(Exception):
    """Lỗi dữ liệu đầu vào: chương trình dừng và báo rõ, không tự sửa."""
