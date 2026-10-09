"""Chặng 8: in kết quả ra màn hình và ghi file.

File ghi ra (thư mục kết quả):
    ket_qua.json          chỉ số độ lệch, điểm, cờ, xếp loại      (gửi người lập DEM được)
    sai_so_tung_diem.csv  tọa độ, z_ref, z_dem, sai số từng điểm  (KHÔNG gửi trước G3)
    ban_ghi_chay.json     phiên bản, seed, mã băm file vào, lệnh  (gửi được)
"""

from __future__ import annotations

import datetime as dt
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import PHIEN_BAN
from .doc_du_lieu import sha256


def _so(x, nd=3):
    if x is None:
        return "-"
    if isinstance(x, (float, np.floating)):
        return f"{x:.{nd}f}" if np.isfinite(x) else "nan"
    return str(x)


def _json_mac_dinh(o):
    if hasattr(o, "item"):
        return o.item()
    return str(o)


def _tom_tat(ma, t):
    gt = t.get("gia_tri") or {}
    if ma == "C1":
        return f"RMSE={_so(gt.get('RMSE'))}, LE90={_so(gt.get('LE90'))}, r={_so(gt.get('r'))}"
    if ma == "C2" and gt:
        return ", ".join(f"{l}: RMSE={_so(v.get('RMSE'))} ({_so(v.get('diem'), 1)}đ, n={v['n']})"
                         for l, v in gt.items())
    if ma == "C3":
        return f"ME={_so(gt.get('ME'))}, ME vùng trống={_so(gt.get('ME_vung_trong'))}"
    if ma == "C4" and gt:
        return f"RMSE độ dốc={_so(gt.get('RMSE_doc_do'))}°, {gt.get('so_cap')} cặp"
    if ma == "C5":
        return f"hợp lệ {_so(gt.get('ty_le_phan_tram'), 2)}%"
    if ma == "C6":
        return ", ".join(f"{k}={'-' if v is None else v}" for k, v in gt.items())
    if ma == "C7":
        return (f"độc lập: {gt.get('doc_lap')} ({gt.get('diem_doc_lap')}), "
                f"n_min={gt.get('n_min')} ({gt.get('diem_co_mau')}), KTC ({gt.get('diem_khoang_tin_cay')})")
    if ma == "C8" and gt:
        return ", ".join(f"{k}={v}" for k, v in gt.items())
    return ""


def in_ket_qua(kq: dict):
    tk = kq["do_lech"]["toan_khu"]
    T = kq["cau_hinh"]["T"]
    print()
    print("=" * 76)
    print(f" KẾT QUẢ KIỂM TRA DEM: {kq['dau_vao']['dem']}")
    print("=" * 76)
    bg = kq["dau_vao"].get("ban_giao")
    if bg:
        print(f" Phiếu bàn giao: {bg}")
    print(f" Điểm kiểm tra dùng: {tk['n']}   (bị loại: {kq['dau_vao']['diem_bi_loai']})   T = {T} m")

    print("\n ĐỘ LỆCH (sai số = DEM - tham chiếu, đơn vị m)")
    print(f"  {'Phạm vi':<12}{'n':>6}{'ME':>9}{'SD':>9}{'MAE':>9}{'RMSE':>9}{'LE90':>9}{'min':>9}{'max':>9}")
    for ten, s in [("toàn khu", tk)] + list(kq["do_lech"]["theo_lop"].items()):
        if s.get("n", 0) == 0:
            print(f"  {ten:<12}{0:>6}   (không có điểm)")
            continue
        print(f"  {ten:<12}{s['n']:>6}{s['ME']:>9.3f}{s['SD']:>9.3f}{s['MAE']:>9.3f}"
              f"{s['RMSE']:>9.3f}{s['LE90']:>9.3f}{s['min']:>9.3f}{s['max']:>9.3f}")

    print("\n KHOẢNG TIN CẬY 95% CỦA RMSE (bootstrap)")
    for k, v in kq["tieu_chi"]["C7"]["gia_tri"]["khoang_tin_cay_RMSE_95"].items():
        if v:
            nhan = "  <- T nằm trong khoảng: sát ngưỡng" if v[0] <= T <= v[1] else ""
            print(f"  {k:<12}[{v[0]:.3f}, {v[1]:.3f}] m, lấy mẫu {v[2]}{nhan}")
    cd = kq.get("spearman_tan")
    if cd:
        print(f"\n Spearman |e| ~ chiều cao tán: rho = {cd['spearman_rho']:.3f}, "
              f"p = {cd['p_value']:.2g}, n = {cd['n']}")

    print("\n ĐIỂM THEO TIÊU CHÍ")
    print(f"  {'Mã':<5}{'Điểm':>11}{'/Tối đa':>9}   Giá trị chính")
    for ma, t in kq["tieu_chi"].items():
        d = t.get("diem")
        ds = "không chấm" if d is None else f"{d:.2f}"
        print(f"  {ma:<5}{ds:>11}{'/' + str(t['toi_da']):>9}   {_tom_tat(ma, t)}")
        if t.get("ghi_chu"):
            print(f"  {'':<25}-> {t['ghi_chu']}")

    x = kq["xep_loai"]
    print(f"\n Tổng thô: {x['tong_tho']:.2f} / {x['toi_da_da_cham']}   "
          f"Tổng quy đổi về 100: {x['tong_quy_doi']:.2f}")
    if x["tieu_chi_khong_cham"]:
        print(f" Không chấm (đã quy đổi): {', '.join(x['tieu_chi_khong_cham'])}")
    for g in x["ghi_chu"]:
        print(f" [LƯU Ý] {g}")
    print(f" Xếp loại theo điểm : {x['xep_loai_theo_diem']}")
    print(f" Xếp loại chính thức: {x['xep_loai_chinh_thuc']}")
    for c in x["dieu_kien_chan"]:
        print(f"   - {c}")
    print(f" Kết luận ở mốc G3  : {x['ket_luan_G3']}")
    print("\n Phần II (D1-D5) do người duyệt chấm theo tài liệu; chương trình không chấm.")
    print("=" * 76)


def ghi_ket_qua(thu_muc: Path, kq: dict, bang_diem: pd.DataFrame, file_vao: dict, seed, bo_doc: str):
    thu_muc.mkdir(parents=True, exist_ok=False)
    bang_diem.to_csv(thu_muc / "sai_so_tung_diem.csv", index=False)
    with open(thu_muc / "ket_qua.json", "w", encoding="utf-8") as f:
        json.dump(kq, f, ensure_ascii=False, indent=2, default=_json_mac_dinh)
    import scipy
    ban_ghi = {
        "thoi_diem": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "phien_ban_chuong_trinh": PHIEN_BAN,
        "python": sys.version.split()[0],
        "he_dieu_hanh": platform.platform(),
        "thu_vien": {"numpy": np.__version__, "pandas": pd.__version__,
                     "scipy": scipy.__version__, "bo_doc_raster": bo_doc},
        "seed": seed,
        "ma_bam": {k: sha256(p) for k, p in file_vao.items() if p},
        "file_vao": {k: str(p) for k, p in file_vao.items() if p},
        "lenh": " ".join(sys.argv),
    }
    with open(thu_muc / "ban_ghi_chay.json", "w", encoding="utf-8") as f:
        json.dump(ban_ghi, f, ensure_ascii=False, indent=2)
