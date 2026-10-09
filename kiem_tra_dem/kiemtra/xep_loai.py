"""Chặng 7: tổng điểm, quy đổi về 100, xếp loại, điều kiện chặn.

Xếp loại (ĐỀ XUẤT):
    Tốt                     tổng >= 85, C1 >= 12, C7 >= 10, không cờ lỗi hệ thống, C8 chạy lại khớp
    Đạt                     tổng 70-84 và C1 >= 12
    Chưa đạt, dùng hạn chế  tổng 50-69, hoặc tổng >= 70 nhưng C1 < 12
    Không đạt               tổng < 50
Chặn xếp loại chính thức khi: C7 phần độc lập = 0, C7 < 8, hoặc có cờ lỗi hệ thống ở C3.
"""

from __future__ import annotations

import math


def xep_loai(tc: dict) -> dict:
    co_diem = {k: v for k, v in tc.items() if v.get("diem") is not None}
    khong_cham = [k for k, v in tc.items() if v.get("diem") is None]
    tong_tho = sum(v["diem"] for v in co_diem.values())
    toi_da = sum(v["toi_da"] for v in co_diem.values())
    tong_qd = tong_tho * 100.0 / toi_da if toi_da else math.nan

    c1, c7 = tc["C1"]["diem"], tc["C7"]["diem"]
    loi_he_thong = bool(tc["C3"].get("co_loi_he_thong"))

    chan = []
    if tc["C7"].get("doc_lap_bang_0"):
        chan.append("C7 phần độc lập bằng 0: chưa xác nhận điểm kiểm tra độc lập, không xếp loại")
    elif c7 < 8:
        chan.append("C7 dưới 8: chưa đủ bằng chứng để kết luận")
    if loi_he_thong:
        chan.append("cờ nghi lỗi hệ thống ở C3: kiểm hệ cao độ, hệ tọa độ rồi chấm lại")

    ghi = []
    if tong_qd >= 85 and c1 >= 12 and c7 >= 10 and not loi_he_thong:
        loai = "Tốt"
        if not tc["C8"].get("chay_lai_khop"):
            loai = "Đạt"
            ghi.append("C8 chưa chứng minh chạy lại ra cùng DEM nên không xếp 'Tốt'")
    elif tong_qd >= 70 and c1 >= 12:
        loai = "Đạt"
    elif tong_qd >= 50:
        loai = "Chưa đạt, dùng hạn chế"
    else:
        loai = "Không đạt"
    if toi_da < 80:
        ghi.append(f"chỉ chấm được {toi_da}/100 điểm tối đa: tổng quy đổi kém tin cậy")

    if chan:
        chinh_thuc, g3 = "CHƯA XẾP LOẠI (vướng điều kiện chặn)", "chưa kết luận"
    else:
        chinh_thuc = loai
        g3 = "DEM đạt" if loai in ("Tốt", "Đạt") else "DEM chưa đạt: chuyển sang chẩn đoán (Phần II)"

    return {"tong_tho": tong_tho, "toi_da_da_cham": toi_da, "tong_quy_doi": tong_qd,
            "tieu_chi_khong_cham": khong_cham, "xep_loai_theo_diem": loai,
            "xep_loai_chinh_thuc": chinh_thuc, "dieu_kien_chan": chan,
            "ghi_chu": ghi, "ket_luan_G3": g3}
