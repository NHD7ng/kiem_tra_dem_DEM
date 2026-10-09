"""Đọc dữ liệu: file DEM .tif, bảng điểm kiểm tra, ranh giới, chiều cao tán.
Lấy cao độ DEM tại điểm bằng nội suy song tuyến và tính sai số.

Chặng 1: đọc .tif và kiểm tra hệ tọa độ, NoData.
Chặng 2: đọc bảng điểm, lấy mẫu DEM tại điểm, gán lớp phủ, tính e = z_dem - z_ref.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

from . import LoiDauVao


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Raster
# --------------------------------------------------------------------------
class Raster:
    """Raster một băng: mảng float64 (NoData -> NaN) và phép biến đổi affine
    x = x0 + cột*sx + hàng*rx ; y = y0 + cột*ry + hàng*sy   (góc trên trái ô)."""

    def __init__(self, data, transform, epsg, nodata, bo_doc, la_he_phang, don_vi):
        self.data = data
        self.transform = transform   # (x0, sx, rx, y0, ry, sy)
        self.epsg = epsg
        self.nodata = nodata
        self.bo_doc = bo_doc
        self.la_he_phang = la_he_phang
        self.don_vi = don_vi

    @property
    def kich_thuoc_o(self):
        _, sx, _, _, _, sy = self.transform
        return abs(sx), abs(sy)

    def toa_do_o(self, x, y):
        """Tọa độ bản đồ -> (hàng, cột) liên tục, gốc tại TÂM ô (0, 0)."""
        x0, sx, rx, y0, ry, sy = self.transform
        dx, dy = np.asarray(x, float) - x0, np.asarray(y, float) - y0
        if rx or ry:
            inv = np.linalg.inv(np.array([[sx, rx], [ry, sy]]))
            col = inv[0, 0] * dx + inv[0, 1] * dy
            row = inv[1, 0] * dx + inv[1, 1] * dy
        else:
            col, row = dx / sx, dy / sy
        return row - 0.5, col - 0.5

    def tam_o(self):
        """Tọa độ bản đồ của tâm mọi ô."""
        h, w = self.data.shape
        x0, sx, rx, y0, ry, sy = self.transform
        cc, rr = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
        return x0 + cc * sx + rr * rx, y0 + cc * ry + rr * sy

    def lay_mau(self, x, y):
        """Nội suy song tuyến. Điểm ngoài DEM hoặc cạnh ô NoData -> NaN."""
        row, col = self.toa_do_o(x, y)
        return ndimage.map_coordinates(self.data, [row, col], order=1,
                                       mode="constant", cval=np.nan)


def doc_raster(path: Path) -> Raster:
    """Đọc GeoTIFF một băng: dùng rasterio nếu có, nếu không thì tifffile."""
    path = Path(path)
    if not path.exists():
        raise LoiDauVao(f"Không thấy file: {path}")
    try:
        import rasterio  # type: ignore
    except ImportError:
        return _doc_tifffile(path)
    return _doc_rasterio(path, rasterio)


def _doc_rasterio(path, rasterio):
    with rasterio.open(path) as src:
        if src.count != 1:
            raise LoiDauVao(f"{path.name}: cần GeoTIFF 1 băng, file có {src.count} băng")
        arr = src.read(1).astype("float64")
        nod = src.nodata
        if nod is not None:
            arr[arr == nod] = np.nan
        t = src.transform
        epsg = src.crs.to_epsg() if src.crs else None
        la_phang = bool(src.crs and src.crs.is_projected)
        don_vi = None
        if la_phang:
            try:
                don_vi = src.crs.linear_units
            except Exception:
                don_vi = None
    return Raster(arr, (t.c, t.a, t.b, t.f, t.d, t.e), epsg, nod, "rasterio", la_phang, don_vi)


def _doc_tifffile(path):
    try:
        import tifffile
    except ImportError as e:
        raise LoiDauVao("Cần cài rasterio hoặc tifffile để đọc GeoTIFF") from e
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        arr = page.asarray()
        tags = {t.code: t.value for t in page.tags.values()}
    if arr.ndim != 2:
        raise LoiDauVao(f"{path.name}: cần GeoTIFF 1 băng, mảng có hình {arr.shape}")
    arr = arr.astype("float64")

    nod = None
    if 42113 in tags:                                   # GDAL_NODATA
        try:
            nod = float(str(tags[42113]).strip().strip("\x00"))
            arr[arr == nod] = np.nan
        except ValueError:
            nod = None

    geokeys = {}
    if 34735 in tags:                                   # GeoKeyDirectory
        g = list(tags[34735])
        for i in range(4, len(g), 4):
            key, loc, _, val = g[i:i + 4]
            if loc == 0:
                geokeys[key] = val

    if 34264 in tags:                                   # ModelTransformation
        m = list(tags[34264])
        sx, rx, x0, ry, sy, y0 = m[0], m[1], m[3], m[4], m[5], m[7]
    elif 33550 in tags and 33922 in tags:               # PixelScale + Tiepoint
        sc, tp = list(tags[33550]), list(tags[33922])
        sx, sy, rx, ry = sc[0], -sc[1], 0.0, 0.0
        x0, y0 = tp[3] - tp[0] * sx, tp[4] - tp[1] * sy
    else:
        raise LoiDauVao(f"{path.name}: không có thông tin tọa độ (không phải GeoTIFF?)")

    if geokeys.get(1025) == 2:                          # PixelIsPoint: dịch nửa ô
        x0 -= 0.5 * sx + 0.5 * rx
        y0 -= 0.5 * ry + 0.5 * sy

    la_phang = 3072 in geokeys
    epsg = geokeys.get(3072) or geokeys.get(2048)
    don_vi = None
    if la_phang:
        don_vi = {9001: "metre", 9002: "foot", 9003: "US survey foot"}.get(
            geokeys.get(3076), "metre (theo EPSG, không khai trong file)")
    return Raster(arr, (x0, sx, rx, y0, ry, sy), epsg, nod, "tifffile", la_phang, don_vi)


def kiem_tra_dem(r: Raster, ten: str):
    """Chặng 1: dừng nếu DEM không dùng được để chấm."""
    if r.epsg is None:
        raise LoiDauVao(f"{ten}: không khai hệ quy chiếu (EPSG). Trả người lập DEM để gán hệ quy chiếu.")
    if not r.la_he_phang:
        raise LoiDauVao(f"{ten}: ở hệ địa lý EPSG:{r.epsg} (đơn vị độ). Cần chuyển sang hệ phẳng "
                        "đơn vị mét, ví dụ: gdalwarp -t_srs EPSG:3414 -r bilinear vao.tif ra.tif")
    if not np.isfinite(r.data).any():
        raise LoiDauVao(f"{ten}: toàn bộ ô là NoData")


# --------------------------------------------------------------------------
# Ranh giới
# --------------------------------------------------------------------------
def doc_ranh_gioi(path: Path) -> list[np.ndarray]:
    """Trả danh sách vòng ngoài của các đa giác (mảng Nx2), cùng hệ với DEM."""
    path = Path(path)
    if not path.exists():
        raise LoiDauVao(f"Không thấy file ranh giới: {path}")
    if path.suffix.lower() == ".gpkg":
        try:
            import geopandas as gpd  # type: ignore
        except ImportError as e:
            raise LoiDauVao("Đọc .gpkg cần geopandas; hoặc xuất ranh giới ra .geojson") from e
        vong = []
        for geom in gpd.read_file(path).geometry:
            for p in getattr(geom, "geoms", [geom]):
                vong.append(np.asarray(p.exterior.coords))
        return vong
    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    vong = []
    for ft in gj.get("features", [gj]):
        geom = ft.get("geometry", ft)
        if geom["type"] == "Polygon":
            vong.append(np.asarray(geom["coordinates"][0], dtype=float))
        elif geom["type"] == "MultiPolygon":
            vong.extend(np.asarray(p[0], dtype=float) for p in geom["coordinates"])
    if not vong:
        raise LoiDauVao(f"{path.name}: không tìm thấy đa giác")
    return vong


def mat_na_ranh_gioi(r: Raster, vong: list[np.ndarray]) -> np.ndarray:
    """Mặt nạ True cho ô có tâm nằm trong ranh giới."""
    from matplotlib.path import Path as MPath
    xs, ys = r.tam_o()
    pts = np.column_stack([xs.ravel(), ys.ravel()])
    mask = np.zeros(pts.shape[0], dtype=bool)
    for v in vong:
        mask |= MPath(v[:, :2]).contains_points(pts)
    mask = mask.reshape(r.data.shape)
    if not mask.any():
        raise LoiDauVao("Ranh giới không phủ ô nào của DEM (ranh giới ở hệ tọa độ khác?)")
    return mask


# --------------------------------------------------------------------------
# Bảng điểm kiểm tra
# --------------------------------------------------------------------------
def _doi_he(df, cot, epsg_tu, epsg_den):
    if epsg_tu is None or int(epsg_tu) == int(epsg_den):
        return df
    try:
        from pyproj import Transformer  # type: ignore
    except ImportError as e:
        raise LoiDauVao(f"Bảng điểm ở EPSG:{epsg_tu}, DEM ở EPSG:{epsg_den}. Cần pyproj để đổi hệ, "
                        "hoặc đổi tọa độ điểm trước khi chạy.") from e
    tr = Transformer.from_crs(int(epsg_tu), int(epsg_den), always_xy=True)
    df = df.copy()
    df[cot["x"]], df[cot["y"]] = tr.transform(df[cot["x"]].to_numpy(), df[cot["y"]].to_numpy())
    return df


def doc_diem(path: Path, cfg: dict, epsg_dem) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise LoiDauVao(f"Không thấy bảng điểm: {path}")
    cot = cfg["cot"]
    if path.suffix.lower() == ".gpkg":
        try:
            import geopandas as gpd  # type: ignore
        except ImportError as e:
            raise LoiDauVao("Đọc .gpkg cần geopandas; hoặc xuất bảng điểm ra .csv") from e
        gdf = gpd.read_file(path)
        if gdf.crs is not None:
            gdf = gdf.to_crs(epsg=int(epsg_dem))
        df = pd.DataFrame(gdf.drop(columns="geometry"))
        df[cot["x"]], df[cot["y"]] = gdf.geometry.x, gdf.geometry.y
    else:
        df = _doi_he(pd.read_csv(path), cot, cfg.get("crs_diem"), epsg_dem)

    thieu = [cot[k] for k in ("x", "y", "z_ref") if cot[k] not in df.columns]
    if thieu:
        raise LoiDauVao(f"{path.name}: thiếu cột {thieu}. Cột hiện có: {list(df.columns)}")
    if cot["id"] not in df.columns:
        df[cot["id"]] = np.arange(1, len(df) + 1)
    if df[cot["id"]].duplicated().any():
        raise LoiDauVao(f"{path.name}: cột {cot['id']} có giá trị trùng")
    return df


def tinh_sai_so(r: Raster, df: pd.DataFrame, cfg: dict, mask=None, tan: Raster | None = None):
    """Chặng 2: lấy cao độ DEM tại điểm, gán lớp phủ, tính e = z_dem - z_ref.

    Trả (bảng mọi điểm, bảng điểm dùng để chấm, số điểm bị loại)."""
    cot = cfg["cot"]
    x = df[cot["x"]].to_numpy(float)
    y = df[cot["y"]].to_numpy(float)
    out = pd.DataFrame({"id": df[cot["id"]].to_numpy(), "x": x, "y": y,
                        "z_ref": df[cot["z_ref"]].to_numpy(float),
                        "z_dem": r.lay_mau(x, y)})
    for c in (cot["tuyen"], cot["thu_tu"], "nguon"):
        if c in df.columns:
            out[c] = df[c].to_numpy()

    # Lớp phủ: ưu tiên cột 'lop' trong bảng; nếu không có thì gán từ chiều cao tán.
    if cot["tan"] in df.columns:
        out["tan"] = df[cot["tan"]].to_numpy(float)
    elif tan is not None:
        if tan.epsg and int(tan.epsg) != int(r.epsg):
            raise LoiDauVao(f"Bản đồ chiều cao tán ở EPSG:{tan.epsg}, DEM ở EPSG:{r.epsg}")
        out["tan"] = tan.lay_mau(x, y)
    if cot["lop"] in df.columns:
        out["lop"] = df[cot["lop"]].astype(str).to_numpy()
    elif "tan" in out.columns:
        lop = np.full(len(out), None, dtype=object)
        for ten, (a, b) in cfg["lop_phu"].items():
            lop[(out["tan"] >= a) & (out["tan"] < b)] = ten
        out["lop"] = lop

    hop_le = np.isfinite(out["z_dem"]) & np.isfinite(out["z_ref"])
    if mask is not None:
        rr, cc = r.toa_do_o(x, y)
        h, w = r.data.shape
        trong_khung = (rr > -0.5) & (cc > -0.5) & (rr < h - 0.5) & (cc < w - 0.5)
        ri = np.clip(np.round(rr).astype(int), 0, h - 1)
        ci = np.clip(np.round(cc).astype(int), 0, w - 1)
        hop_le &= trong_khung & mask[ri, ci]
    out["e"] = out["z_dem"] - out["z_ref"]
    out["dung_de_cham"] = hop_le
    dung = out[hop_le].copy()
    if len(dung) < 2:
        raise LoiDauVao("Dưới 2 điểm hợp lệ sau khi lấy mẫu. Kiểm tra hệ tọa độ của bảng điểm "
                        "và ranh giới so với DEM.")
    return out, dung, int((~hop_le).sum())
