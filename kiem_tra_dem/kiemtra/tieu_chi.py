"""Chặng 5-6: điểm từng tiêu chí C1-C8.

Mỗi hàm trả một dict:
    diem      điểm (None nếu không đủ dữ liệu để chấm)
    toi_da    điểm tối đa
    gia_tri   các giá trị đo được
    ghi_chu   lý do trừ điểm, không chấm, cảnh báo

Thang điểm theo tài liệu "Bộ tiêu chí chấm điểm DEM" (ĐỀ XUẤT).
Giữa hai mốc: nội suy tuyến tính. Dưới mốc đầu: điểm mốc đầu. Vượt mốc cuối: 0.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from .cau_hinh import duong_dan
from .do_lech import bootstrap_rmse, rmse
from .doc_du_lieu import Raster, doc_raster, sha256


def noi_suy(x, moc_x, moc_y) -> float:
    if x is None or not np.isfinite(x):
        return 0.0
    return float(np.interp(x, moc_x, moc_y, right=0.0))


def khong_cham(toi_da, ly_do, **them):
    return {"diem": None, "toi_da": toi_da, "gia_tri": them.get("gia_tri", {}), "ghi_chu": ly_do, **{
        k: v for k, v in them.items() if k != "gia_tri"}}


# C1 -----------------------------------------------------------------------
def cham_C1(tk: dict, T: float) -> dict:
    """RMSE và LE90 toàn khu (20 điểm)."""
    r = tk["RMSE"] / T
    diem = noi_suy(r, [0.5, 0.75, 1.0, 1.5, 2.0], [20, 16, 12, 6, 2])
    tru = 4.0 if tk["LE90"] > 2 * T else 0.0
    return {"diem": max(0.0, diem - tru), "toi_da": 20,
            "gia_tri": {"RMSE": tk["RMSE"], "LE90": tk["LE90"], "r": r},
            "ghi_chu": "trừ 4 điểm vì LE90 > 2T" if tru else ""}


# C2 -----------------------------------------------------------------------
def cham_C2(dung, cfg) -> dict:
    """RMSE theo lớp phủ (15 điểm, mỗi lớp tối đa 5)."""
    if "lop" not in dung.columns or dung["lop"].isna().all():
        return khong_cham(15, "không có cột lớp phủ hay bản đồ chiều cao tán")
    T = cfg["T"]
    chi_tiet, tong = {}, 0.0
    for l in cfg["lop_phu"]:
        e = dung.loc[dung["lop"] == l, "e"].to_numpy()
        if e.size == 0:
            chi_tiet[l] = {"n": 0, "diem": 0.0, "ghi_chu": "không có điểm"}
            continue
        r = rmse(e) / T
        s = noi_suy(r, [1.0, 1.5, 2.0], [5, 3, 1])
        gc = ""
        if e.size < 10:
            s, gc = min(s, 2.0), "dưới 10 điểm: tối đa 2"
        chi_tiet[l] = {"n": int(e.size), "RMSE": rmse(e), "r": r, "diem": s, "ghi_chu": gc}
        tong += s
    return {"diem": tong, "toi_da": 15, "gia_tri": chi_tiet, "ghi_chu": ""}


# C3 -----------------------------------------------------------------------
def cham_C3(tk: dict, dung, cfg) -> dict:
    """Độ lệch hệ thống ME (10 điểm); cờ nghi lỗi hệ thống ở vùng trống."""
    T = cfg["T"]
    me = tk["ME"]
    diem = noi_suy(abs(me) / T, [0.1, 0.25, 0.5, 1.0], [10, 7, 4, 1])
    lv = cfg["lop_vung_trong"]
    me_trong, co = None, False
    if "lop" in dung.columns and (dung["lop"] == lv).any():
        me_trong = float(dung.loc[dung["lop"] == lv, "e"].mean())
        co = abs(me_trong) > 0.25 * T
        if co:
            diem = min(diem, 3.0)
    if co:
        gc = "NGHI LỖI HỆ THỐNG: |ME vùng trống| > 0,25T (kiểm hệ cao độ, hệ tọa độ)"
    elif me_trong is None:
        gc = "không có lớp vùng trống để kiểm lỗi hệ thống"
    else:
        gc = ""
    return {"diem": diem, "toi_da": 10,
            "gia_tri": {"ME": me, "abs_ME_chia_T": abs(me) / T, "ME_vung_trong": me_trong},
            "co_loi_he_thong": co, "ghi_chu": gc}


# C4 -----------------------------------------------------------------------
def cham_C4(dung, cfg) -> dict:
    """Sai số độ dốc dọc tuyến (10 điểm)."""
    T_doc = cfg.get("T_doc")
    cot = cfg["cot"]
    if not T_doc:
        return khong_cham(10, "chưa khai T_doc trong cấu hình")
    if cot["tuyen"] not in dung.columns or cot["thu_tu"] not in dung.columns:
        return khong_cham(10, "bảng điểm không có cột tuyến/thứ tự")
    dmin, dmax = cfg["doc_do_doc"]["d_min"], cfg["doc_do_doc"]["d_max"]
    delta = []
    for _, g in dung.sort_values(cot["thu_tu"]).groupby(cot["tuyen"]):
        g = g.reset_index(drop=True)
        for i in range(len(g) - 1):
            a, b = g.iloc[i], g.iloc[i + 1]
            if "lop" in g.columns and a.get("lop") != b.get("lop"):
                continue                       # không ghép cặp xuyên lớp phủ
            d = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
            if not (dmin <= d <= dmax):
                continue
            t_ref = math.degrees(math.atan((b["z_ref"] - a["z_ref"]) / d))
            t_dem = math.degrees(math.atan((b["z_dem"] - a["z_dem"]) / d))
            delta.append(t_dem - t_ref)
    if len(delta) < 2:
        return khong_cham(10, f"chỉ có {len(delta)} cặp điểm hợp lệ (d trong [{dmin}, {dmax}] m)")
    rm = rmse(delta)
    r = rm / T_doc
    return {"diem": noi_suy(r, [0.5, 0.75, 1.0, 1.5, 2.0], [10, 8, 6, 3, 1]), "toi_da": 10,
            "gia_tri": {"so_cap": len(delta), "RMSE_doc_do": rm, "r": r}, "ghi_chu": ""}


# C5 -----------------------------------------------------------------------
def cham_C5(r: Raster, mask) -> dict:
    """Tỷ lệ ô hợp lệ trong ranh giới (10 điểm)."""
    hop_le = np.isfinite(r.data)
    gc = ""
    if mask is None:
        mask = np.ones_like(hop_le, dtype=bool)
        gc = "không có ranh giới: tính trên toàn bộ DEM"
    n_tong = int(mask.sum())
    n_hl = int((hop_le & mask).sum())
    ty_le = 100.0 * n_hl / n_tong
    return {"diem": noi_suy(-ty_le, [-99, -95, -90, -80], [10, 7, 4, 1]), "toi_da": 10,
            "gia_tri": {"o_hop_le": n_hl, "o_trong_ranh_gioi": n_tong, "ty_le_phan_tram": ty_le},
            "ghi_chu": gc}


# C6 -----------------------------------------------------------------------
def cham_C6(r: Raster, cfg) -> dict:
    """Nhất quán kỹ thuật: 5 mục x 2 điểm. Mục 3, 4 do người duyệt điền."""
    muc = {}
    hc = cfg["he_cao_do"]
    co_he_cao_do = bool(hc.get("dem")) and bool(hc.get("diem"))
    muc["1_he_quy_chieu"] = (2 if co_he_cao_do else 1) if (r.epsg and r.la_he_phang) else 0

    v = r.data[np.isfinite(r.data)]
    lo, hi = cfg["cao_do_hop_ly"]
    trong_khoang = v.size > 0 and v.min() >= lo and v.max() <= hi
    don_vi_m = r.don_vi is None or str(r.don_vi).startswith("metre")
    muc["2_don_vi_nodata"] = int(r.nodata is not None) + int(trong_khoang and don_vi_m)

    yc = cfg.get("do_phan_giai")
    if yc:
        sx, sy = r.kich_thuoc_o
        muc["5_do_phan_giai"] = 2 if abs(sx - yc) <= 0.01 * yc and abs(sy - yc) <= 0.01 * yc else 0
    else:
        muc["5_do_phan_giai"] = None

    tc = cfg["kiem_tra_thu_cong"]
    muc["3_loi_hinh_anh"] = tc.get("loi_hinh_anh")
    muc["4_mep_ghep"] = tc.get("mep_ghep")

    ghi = []
    if not co_he_cao_do:
        ghi.append("chưa khai hệ cao độ (he_cao_do.dem / he_cao_do.diem)")
    if r.nodata is None:
        ghi.append("DEM không khai NoData")
    if v.size and not trong_khoang:
        ghi.append(f"cao độ ngoài khoảng hợp lý [{lo}, {hi}] m: min={v.min():.1f}, max={v.max():.1f}")
    thieu = [k for k, x in muc.items() if x is None]
    if thieu:
        return {"diem": None, "toi_da": 10, "gia_tri": muc,
                "ghi_chu": "; ".join(["chưa đủ để chấm, thiếu mục: " + ", ".join(thieu)] + ghi),
                "diem_tam_tu_dong": float(sum(x for x in muc.values() if x is not None))}
    return {"diem": float(sum(muc.values())), "toi_da": 10, "gia_tri": muc, "ghi_chu": "; ".join(ghi)}


# C7 -----------------------------------------------------------------------
def cham_C7(dung, cfg, diem_path: Path | None, rng) -> dict:
    """Độ tin cậy của kiểm chứng: độc lập (5) + cỡ mẫu (5) + khoảng tin cậy (5)."""
    kc = cfg["kiem_chung"]
    ghi = []
    ma_bam_khop = None
    if kc.get("sha256_diem") and diem_path is not None:
        ma_bam_khop = sha256(diem_path) == str(kc["sha256_diem"]).strip().lower()
        if not ma_bam_khop:
            ghi.append("mã băm bảng điểm KHÔNG khớp mã đã đóng băng")
    elif not kc.get("sha256_diem"):
        ghi.append("chưa khai mã băm bảng điểm đã đóng băng")

    if kc.get("doc_lap") is True and ma_bam_khop is not False:
        p1, doc_lap = 5, "đã xác nhận"
    elif kc.get("doc_lap") is False or ma_bam_khop is False:
        p1, doc_lap = 0, "vi phạm"
    else:
        p1, doc_lap = 0, "chưa xác nhận"
        ghi.append("chưa xác nhận tính độc lập (kiem_chung.doc_lap)")

    if "lop" in dung.columns and dung["lop"].notna().any():
        dem_lop = {l: int((dung["lop"] == l).sum()) for l in cfg["lop_phu"]}
        n_min = min(dem_lop.values())
    else:
        dem_lop, n_min = {}, int(len(dung))
        ghi.append("không có lớp phủ: dùng tổng số điểm")
    p2 = 5 if n_min >= 30 else 3 if n_min >= 20 else 1 if n_min >= 10 else 0

    cot_tuyen = cfg["cot"]["tuyen"]
    nhom = cot_tuyen if cot_tuyen in dung.columns else None
    n_boot = int(cfg["bootstrap"]["n"])
    ktc = {"toan_khu": bootstrap_rmse(dung["e"], dung[nhom] if nhom else None, n_boot, rng)}
    du_lop = bool(dem_lop)
    for l in dem_lop:
        sub = dung[dung["lop"] == l]
        ktc[l] = bootstrap_rmse(sub["e"], sub[nhom] if nhom else None, n_boot, rng)
        du_lop &= ktc[l] is not None
    p3 = 5 if du_lop else (3 if ktc["toan_khu"] else 0)

    return {"diem": float(p1 + p2 + p3), "toi_da": 15,
            "gia_tri": {"doc_lap": doc_lap, "diem_doc_lap": p1, "so_diem_moi_lop": dem_lop,
                        "n_min": n_min, "diem_co_mau": p2, "khoang_tin_cay_RMSE_95": ktc,
                        "diem_khoang_tin_cay": p3},
            "doc_lap_bang_0": p1 == 0, "ghi_chu": "; ".join(ghi)}


# C8 -----------------------------------------------------------------------
def cham_C8(r: Raster, dem_lai: Path | None, cfg, cfg_dir: Path | None) -> dict:
    """Tái lập: chạy lại (4) + nguồn và tham số (3) + môi trường (2) + nhật ký (1)."""
    if dem_lai is None:
        return khong_cham(10, "chưa có DEM chạy lại (--dem-chay-lai)", chay_lai_khop=False)
    tl = cfg["tai_lap"]
    gia_tri, ghi = {}, []

    r2 = doc_raster(dem_lai)
    if r2.data.shape != r.data.shape:
        p1 = 0
        ghi.append(f"DEM chạy lại khác kích thước {r2.data.shape} so với {r.data.shape}")
    else:
        a, b = r.data, r2.data
        cung_nan = bool(np.array_equal(np.isnan(a), np.isnan(b)))
        ok = np.isfinite(a) & np.isfinite(b)
        lech = float(np.max(np.abs(a[ok] - b[ok]))) if ok.any() else float("nan")
        gia_tri.update({"lech_lon_nhat_m": lech, "cung_vi_tri_nodata": cung_nan})
        p1 = 4 if (cung_nan and lech <= tl["dung_sai"]) else 1
        if p1 < 4:
            ghi.append("DEM chạy lại lệch vượt dung sai: cần ghi nguyên nhân")

    nguon = tl.get("nguon_du_lieu") or []
    a_ok = bool(nguon) and all(all(n.get(k) for k in ("ten", "phien_ban", "ngay_tai")) for n in nguon)
    b_ok = bool(nguon)
    for n in nguon:
        p = duong_dan(n.get("duong_dan"), cfg_dir)
        if not (p and n.get("sha256")):
            b_ok = False
        elif not p.exists() or sha256(p) != str(n["sha256"]).strip().lower():
            b_ok = False
            ghi.append(f"mã băm không khớp hoặc thiếu file: {n.get('duong_dan')}")
    p2 = int(a_ok) + int(b_ok) + int(cfg_dir is not None)

    env = duong_dan(tl.get("moi_truong"), cfg_dir)
    if env is not None and env.exists():
        p3 = 2 if tl.get("moi_truong_tao_lai_duoc") is True else 1
        if p3 == 1:
            ghi.append("có file môi trường nhưng chưa xác nhận tạo lại được")
    else:
        p3 = 0
    nk = duong_dan(tl.get("nhat_ky"), cfg_dir)
    p4 = 1 if (nk and nk.exists()) else 0

    gia_tri.update({"phan1_chay_lai": p1, "phan2_nguon_tham_so": p2,
                    "phan3_moi_truong": p3, "phan4_nhat_ky": p4})
    return {"diem": float(p1 + p2 + p3 + p4), "toi_da": 10, "gia_tri": gia_tri,
            "chay_lai_khop": p1 == 4, "ghi_chu": "; ".join(ghi)}
