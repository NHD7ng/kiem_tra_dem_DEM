"""Cấu hình: giá trị mặc định, đọc file .yaml, đọc phiếu bàn giao.

Mọi ngưỡng và thang điểm là ĐỀ XUẤT, đổi trong file .yaml của từng khu.
Đường dẫn tương đối trong file cấu hình được tính từ thư mục chứa file đó.
"""

from __future__ import annotations

import copy
from pathlib import Path

from . import LoiDauVao

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


MAC_DINH = {
    "T": 2.0,                       # m, ngưỡng RMSE yêu cầu (chốt ở G1)
    "T_doc": None,                  # độ, ngưỡng RMSE độ dốc; None = không chấm C4
    "do_phan_giai": None,           # m, độ phân giải yêu cầu; None = không kiểm
    "lop_phu": {                    # chiều cao tán (m): [từ, đến)
        "trong": [0, 5],
        "thua": [5, 20],
        "day": [20, 1e9],
    },
    "lop_vung_trong": "trong",      # lớp dùng để kiểm lỗi hệ thống (C3)
    "cao_do_hop_ly": [-50, 300],    # m, khoảng cao độ hợp lý của khu vực
    "he_cao_do": {"dem": None, "diem": None},
    "crs_diem": None,               # EPSG của bảng điểm .csv; None = cùng hệ với DEM
    "loc_diem": None,               # biểu thức lọc pandas, ví dụ "co_chat_luong == 0"
    "du_lieu": {                    # đường dẫn dữ liệu tham chiếu (có thể thay bằng tham số)
        "diem": None,
        "ranh_gioi": None,
        "tan": None,
    },
    "bootstrap": {"n": 2000, "seed": 42},
    "doc_do_doc": {"d_min": 80, "d_max": 120},   # m, khoảng cách cặp điểm cho C4
    "kiem_chung": {
        "doc_lap": None,            # true/false: B xác nhận điểm kiểm tra độc lập
        "sha256_diem": None,        # mã băm bảng điểm đã đóng băng
    },
    "kiem_tra_thu_cong": {          # B điền 0, 1 hoặc 2 sau khi xem bản đồ bóng đổ
        "loi_hinh_anh": None,       # C6 mục 3
        "mep_ghep": None,           # C6 mục 4
    },
    "tai_lap": {
        "dung_sai": 1e-6,           # m
        "nguon_du_lieu": [],        # [{ten, phien_ban, ngay_tai, duong_dan, sha256}]
        "moi_truong": "../environment.yml",
        "moi_truong_tao_lai_duoc": None,
        "nhat_ky": None,
    },
    "cot": {
        "id": "id", "x": "x", "y": "y", "z_ref": "z_ref",
        "lop": "lop", "tan": "chieu_cao_tan",
        "tuyen": "tuyen", "thu_tu": "thu_tu",
    },
}


def _gop(goc: dict, them: dict) -> dict:
    kq = copy.deepcopy(goc)
    for k, v in (them or {}).items():
        if isinstance(v, dict) and isinstance(kq.get(k), dict):
            kq[k] = _gop(kq[k], v)
        else:
            kq[k] = v
    return kq


def _doc_yaml(path: Path) -> dict:
    if yaml is None:
        raise LoiDauVao("Cần cài pyyaml để đọc file .yaml (conda install -c conda-forge pyyaml)")
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise LoiDauVao(f"{path.name}: file .yaml sai cú pháp: {e}") from e


def doc_cau_hinh(path: Path | None) -> tuple[dict, Path | None]:
    """Trả (cấu hình đã gộp với mặc định, thư mục chứa file cấu hình)."""
    if path is None:
        return copy.deepcopy(MAC_DINH), None
    path = Path(path).resolve()
    if not path.exists():
        raise LoiDauVao(f"Không thấy file cấu hình: {path}")
    return _gop(MAC_DINH, _doc_yaml(path)), path.parent


def duong_dan(gia_tri, thu_muc: Path | None) -> Path | None:
    """Đổi đường dẫn trong cấu hình thành tuyệt đối (tương đối theo thư mục cấu hình)."""
    if not gia_tri:
        return None
    p = Path(gia_tri)
    if not p.is_absolute() and thu_muc is not None:
        p = thu_muc / p
    return p.resolve()


def doc_ban_giao(path: Path) -> dict:
    """Đọc phiếu bàn giao do người lập DEM điền."""
    return _doc_yaml(Path(path))
