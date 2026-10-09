"""Chặng 3-4: các chỉ số độ lệch.

Sai số e = z_dem - z_ref (m). Dương nghĩa là DEM cao hơn thực tế.
    ME   = trung bình e                       (lệch có hướng)
    SD   = độ lệch chuẩn quần thể của e       (RMSE^2 = ME^2 + SD^2)
    MAE  = trung bình |e|
    RMSE = căn của trung bình e^2
    LE90 = phân vị 90 của |e|
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def rmse(e) -> float:
    e = np.asarray(e, dtype=float)
    return float(np.sqrt(np.mean(e ** 2))) if e.size else float("nan")


def thong_ke(e) -> dict:
    e = np.asarray(e, dtype=float)
    if e.size == 0:
        return {"n": 0}
    return {
        "n": int(e.size),
        "ME": float(np.mean(e)),
        "SD": float(np.std(e)),
        "MAE": float(np.mean(np.abs(e))),
        "RMSE": rmse(e),
        "LE90": float(np.percentile(np.abs(e), 90)),
        "min": float(np.min(e)),
        "max": float(np.max(e)),
        "trung_vi": float(np.median(e)),
    }


def thong_ke_theo_lop(dung, lop_phu: dict) -> dict:
    if "lop" not in dung.columns:
        return {}
    return {l: thong_ke(dung.loc[dung["lop"] == l, "e"]) for l in lop_phu}


def bootstrap_rmse(e, nhom, n_boot: int, rng):
    """Khoảng tin cậy 95% của RMSE.
    Có nhóm (mã tuyến) thì lấy mẫu lại nguyên cả tuyến, vì điểm trên một tuyến tương quan."""
    e = np.asarray(e, dtype=float)
    if e.size < 2:
        return None
    vals = []
    if nhom is not None:
        nhom = np.asarray(nhom)
        ma = np.unique(nhom)
        if ma.size >= 2:
            chi_so = {m: np.flatnonzero(nhom == m) for m in ma}
            for _ in range(n_boot):
                idx = np.concatenate([chi_so[m] for m in rng.choice(ma, size=ma.size, replace=True)])
                vals.append(rmse(e[idx]))
            return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), "theo tuyến"]
    for _ in range(n_boot):
        vals.append(rmse(rng.choice(e, size=e.size, replace=True)))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), "theo điểm"]


def spearman_tan(dung):
    """Tương quan hạng giữa |e| và chiều cao tán (bằng chứng cho giả thuyết A)."""
    if "tan" not in dung.columns or dung["tan"].notna().sum() < 5:
        return None
    sub = dung.dropna(subset=["tan"])
    rho, p = stats.spearmanr(sub["tan"], np.abs(sub["e"]))
    return {"spearman_rho": float(rho), "p_value": float(p), "n": int(len(sub))}
