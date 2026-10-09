#!/usr/bin/env python3
"""
chay_kiem_tra.py - Kiểm tra và chấm điểm file DEM .tif theo bộ tiêu chí C1-C8.

Cách dùng:
    python chay_kiem_tra.py <file_dem.tif> --config cau_hinh/khu1.yaml

Dữ liệu tham chiếu (bảng điểm, ranh giới, chiều cao tán) lấy từ mục du_lieu
trong file cấu hình, hoặc chỉ định bằng --diem, --ranh-gioi, --tan.
Nếu cạnh file DEM có ban_giao.yaml, chương trình tự kiểm mã băm của DEM.

Ví dụ đầy đủ:
    python chay_kiem_tra.py nhan_ban_giao/2026-10-10_khu1_v1/khu1.tif \
        --config cau_hinh/khu1.yaml \
        --diem du_lieu_tham_chieu/khu1_diem_kiem_tra.csv \
        --ranh-gioi du_lieu_tham_chieu/khu1_ranh_gioi.geojson \
        --tan du_lieu_tham_chieu/khu1_chieu_cao_tan.tif \
        --ra ket_qua/2026-10-10_khu1_v1
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import numpy as np

from kiemtra import LoiDauVao
from kiemtra.bao_cao import ghi_ket_qua, in_ket_qua
from kiemtra.cau_hinh import doc_ban_giao, doc_cau_hinh, duong_dan
from kiemtra.do_lech import spearman_tan, thong_ke, thong_ke_theo_lop
from kiemtra.doc_du_lieu import (doc_diem, doc_ranh_gioi, doc_raster, kiem_tra_dem,
                                 mat_na_ranh_gioi, sha256, tinh_sai_so)
from kiemtra.tieu_chi import (cham_C1, cham_C2, cham_C3, cham_C4, cham_C5, cham_C6,
                              cham_C7, cham_C8)
from kiemtra.xep_loai import xep_loai


def _thu_muc_ra(args, dem_path: Path) -> Path:
    if args.ra:
        p = Path(args.ra).resolve()
    else:
        ten = dem_path.parent.name if dem_path.parent.name else dem_path.stem
        p = Path("ket_qua").resolve() / f"{ten}_{dt.datetime.now():%Y-%m-%d_%H%M}"
    if p.exists():
        raise LoiDauVao(f"Thư mục kết quả đã tồn tại: {p}. Kết quả không ghi đè, hãy đặt tên khác (--ra).")
    return p


def _kiem_ban_giao(path: Path, dem_path: Path, epsg_dem, cfg: dict) -> dict:
    """So mã băm DEM với phiếu bàn giao; lấy hệ cao độ nếu cấu hình chưa khai."""
    bg = doc_ban_giao(path)
    ma = str(bg.get("sha256") or "").strip().lower()
    if ma:
        that = sha256(dem_path)
        if that != ma:
            raise LoiDauVao(f"Mã băm DEM không khớp phiếu bàn giao.\n  phiếu: {ma}\n  file : {that}\n"
                            "  File đã bị đổi sau khi giao, hoặc phiếu điền sai. Hỏi lại người lập DEM.")
        print("      mã băm DEM khớp phiếu bàn giao")
    else:
        print("      [LƯU Ý] phiếu bàn giao chưa có sha256, không kiểm được file có bị đổi hay không")

    htd = str(bg.get("he_toa_do") or "")
    if htd and epsg_dem and str(epsg_dem) not in htd:
        print(f"      [LƯU Ý] phiếu ghi hệ tọa độ '{htd}' nhưng DEM là EPSG:{epsg_dem}")
    if bg.get("he_cao_do") and not cfg["he_cao_do"].get("dem"):
        cfg["he_cao_do"]["dem"] = bg["he_cao_do"]
        print(f"      hệ cao độ DEM lấy từ phiếu: {bg['he_cao_do']}")
    if bg.get("chua_xem_diem_kiem_tra") is False:
        cfg["kiem_chung"]["doc_lap"] = False
        print("      [CẢNH BÁO] phiếu ghi người lập DEM ĐÃ xem điểm kiểm tra: C7 độc lập = 0")
    return bg


def chay(args) -> int:
    dem_path = Path(args.dem).resolve()
    cfg, cfg_dir = doc_cau_hinh(Path(args.config) if args.config else None)
    if args.T:
        cfg["T"] = args.T
    if cfg_dir is None:
        print("[LƯU Ý] không có file cấu hình: dùng giá trị mặc định (T = 2 m)")

    # Đường dẫn: tham số dòng lệnh ưu tiên hơn mục du_lieu trong cấu hình
    du = cfg["du_lieu"]
    diem_path = Path(args.diem).resolve() if args.diem else duong_dan(du.get("diem"), cfg_dir)
    rg_path = Path(args.ranh_gioi).resolve() if args.ranh_gioi else duong_dan(du.get("ranh_gioi"), cfg_dir)
    tan_path = Path(args.tan).resolve() if args.tan else duong_dan(du.get("tan"), cfg_dir)
    bg_path = Path(args.ban_giao).resolve() if args.ban_giao else dem_path.parent / "ban_giao.yaml"
    if not bg_path.exists():
        bg_path = None
    if diem_path is None:
        raise LoiDauVao("Chưa có bảng điểm kiểm tra: dùng --diem hoặc khai du_lieu.diem trong cấu hình")
    out_dir = _thu_muc_ra(args, dem_path)

    print(f"[1/6] Đọc và kiểm tra DEM: {dem_path.name}")
    r = doc_raster(dem_path)
    kiem_tra_dem(r, dem_path.name)
    sx, sy = r.kich_thuoc_o
    print(f"      bộ đọc={r.bo_doc}, EPSG:{r.epsg}, kích thước {r.data.shape}, "
          f"ô {sx:g} x {sy:g} m, NoData={r.nodata}")
    if bg_path:
        print(f"      phiếu bàn giao: {bg_path.name}")
        _kiem_ban_giao(bg_path, dem_path, r.epsg, cfg)
    else:
        print("      [LƯU Ý] không có phiếu bàn giao cạnh DEM")

    print("[2/6] Đọc dữ liệu tham chiếu")
    for ten, p in (("điểm kiểm tra", diem_path), ("ranh giới", rg_path), ("chiều cao tán", tan_path)):
        print(f"      {ten:<14}: {p if p else '(không có)'}")
    mask = mat_na_ranh_gioi(r, doc_ranh_gioi(rg_path)) if rg_path else None
    tan = doc_raster(tan_path) if tan_path else None
    df = doc_diem(diem_path, cfg, r.epsg)
    n0 = len(df)
    if cfg.get("loc_diem"):
        try:
            df = df.query(cfg["loc_diem"])
        except Exception as e:
            raise LoiDauVao(f"Biểu thức loc_diem lỗi: {cfg['loc_diem']} ({e})") from e
        print(f"      lọc '{cfg['loc_diem']}': giữ {len(df)}/{n0} điểm")

    print("[3/6] Lấy cao độ DEM tại điểm (nội suy song tuyến), tính sai số")
    bang, dung, bi_loai = tinh_sai_so(r, df, cfg, mask=mask, tan=tan)
    print(f"      {len(dung)} điểm dùng để chấm, {bi_loai} điểm bị loại "
          "(ngoài DEM, ngoài ranh giới hoặc sát NoData)")

    print("[4/6] Tính độ lệch")
    tk = thong_ke(dung["e"])
    theo_lop = thong_ke_theo_lop(dung, cfg["lop_phu"])

    print("[5/6] Chấm tiêu chí C1-C8")
    rng = np.random.default_rng(int(cfg["bootstrap"]["seed"]))
    tc = {
        "C1": cham_C1(tk, cfg["T"]),
        "C2": cham_C2(dung, cfg),
        "C3": cham_C3(tk, dung, cfg),
        "C4": cham_C4(dung, cfg),
        "C5": cham_C5(r, mask),
        "C6": cham_C6(r, cfg),
        "C7": cham_C7(dung, cfg, diem_path, rng),
        "C8": cham_C8(r, Path(args.dem_chay_lai).resolve() if args.dem_chay_lai else None, cfg, cfg_dir),
    }
    kq = {
        "dau_vao": {"dem": dem_path.name, "ban_giao": bg_path.name if bg_path else None,
                    "diem": diem_path.name, "diem_bi_loai": bi_loai},
        "cau_hinh": {"T": cfg["T"], "T_doc": cfg.get("T_doc"), "lop_phu": cfg["lop_phu"],
                     "he_cao_do": cfg["he_cao_do"]},
        "do_lech": {"toan_khu": tk, "theo_lop": theo_lop},
        "spearman_tan": spearman_tan(dung),
        "tieu_chi": tc,
        "xep_loai": xep_loai(tc),
    }

    print("[6/6] Ghi kết quả")
    file_vao = {"dem": dem_path, "ban_giao": bg_path, "cau_hinh": Path(args.config).resolve() if args.config else None,
                "diem": diem_path, "ranh_gioi": rg_path, "chieu_cao_tan": tan_path}
    ghi_ket_qua(out_dir, kq, bang, file_vao, cfg["bootstrap"]["seed"], r.bo_doc)
    print(f"      {out_dir}")
    in_ket_qua(kq)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kiểm tra và chấm điểm file DEM .tif theo tiêu chí C1-C8")
    ap.add_argument("dem", help="file DEM .tif (GeoTIFF 1 băng, hệ phẳng đơn vị mét)")
    ap.add_argument("--config", help="file cấu hình .yaml của khu vực")
    ap.add_argument("--diem", help="bảng điểm kiểm tra .csv (hoặc .gpkg)")
    ap.add_argument("--ranh-gioi", help="ranh giới khu vực .geojson (hoặc .gpkg)")
    ap.add_argument("--tan", help="bản đồ chiều cao tán .tif, để gán lớp phủ")
    ap.add_argument("--ban-giao", help="phiếu bàn giao .yaml (mặc định: ban_giao.yaml cạnh DEM)")
    ap.add_argument("--dem-chay-lai", help="DEM do người lập chạy lại trên máy khác, để chấm C8")
    ap.add_argument("--T", type=float, help="ghi đè ngưỡng RMSE T (m)")
    ap.add_argument("--ra", help="thư mục ghi kết quả (không được trùng thư mục đã có)")
    args = ap.parse_args(argv)
    try:
        return chay(args)
    except LoiDauVao as e:
        print(f"\n[LỖI ĐẦU VÀO] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
