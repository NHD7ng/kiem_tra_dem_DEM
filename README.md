# Chương trình kiểm tra DEM

Chương trình này **chấm điểm một file DEM** (`.tif`) xem nó tốt đến đâu. Nó so cao độ trong DEM với cao độ đo được ở các điểm tham chiếu (GEDI, ICESat-2, mốc độ cao), rồi cho biết:

- DEM sai bao nhiêu mét, cao hơn hay thấp hơn thực tế;
- sai nhiều ở vùng trống hay dưới tán rừng;
- điểm theo 8 tiêu chí (C1 đến C8) và xếp loại: Tốt, Đạt, Chưa đạt, Không đạt.

Chương trình **không lập DEM** và **không sửa DEM**. Nó chỉ đọc file và chấm.

```
  Người lập DEM                 Người kiểm tra                    Kết quả
 ┌──────────────┐   giao     ┌──────────────────────┐   chạy   ┌──────────────────┐
 │ khu1.tif     │ ─────────► │ + điểm tham chiếu    │ ───────► │ bảng sai số      │
 │ ban_giao.yaml│            │ + ranh giới, tán     │          │ điểm C1–C8       │
 └──────────────┘            │ + file cấu hình      │          │ xếp loại         │
                             └──────────────────────┘          └──────────────────┘
```

Chi tiết kỹ thuật (công thức, thang điểm, quy trình theo mốc) nằm trong `TAI_LIEU_KY_THUAT.md`. File này chỉ hướng dẫn cách dùng.

---

## Mục lục

1. [Ai làm gì](#1-ai-làm-gì)
2. [Cài đặt lần đầu](#2-cài-đặt-lần-đầu)
3. [Sắp xếp thư mục](#3-sắp-xếp-thư-mục)
4. [Chuẩn bị file](#4-chuẩn-bị-file)
5. [Điền file cấu hình](#5-điền-file-cấu-hình)
6. [Chạy chương trình](#6-chạy-chương-trình)
7. [Đọc kết quả](#7-đọc-kết-quả)
8. [Sau khi chạy](#8-sau-khi-chạy)
9. [Khi chương trình báo lỗi](#9-khi-chương-trình-báo-lỗi)
10. [Câu hỏi thường gặp](#10-câu-hỏi-thường-gặp)

---

## 1. Ai làm gì

| Người | Việc | Cần đọc mục |
| --- | --- | --- |
| **Người lập DEM** | Giao file `.tif` và phiếu `ban_giao.yaml` | 4.1, 7, 9 |
| **Người kiểm tra** | Giữ dữ liệu tham chiếu, chạy chương trình, gửi kết quả | Toàn bộ |

Quy tắc quan trọng nhất: **người lập DEM không được xem dữ liệu tham chiếu** (thư mục `du_lieu_tham_chieu/`) trước khi DEM được chấm. Nếu DEM được chỉnh dựa trên chính các điểm dùng để chấm, kết quả sẽ đẹp giả.

---

## 2. Cài đặt lần đầu

Chỉ làm một lần trên mỗi máy. Chạy được trên Windows, macOS và Linux.

**Bước 1. Cài Conda** nếu máy chưa có: tải Miniforge (hoặc Anaconda) và cài theo hướng dẫn trên trang của nó.

**Bước 2. Mở cửa sổ dòng lệnh:**
- Windows: mở **Miniforge Prompt** (hoặc Anaconda Prompt) từ menu Start.
- macOS, Linux: mở **Terminal**.

**Bước 3. Đi vào thư mục chương trình** (thay đường dẫn bằng chỗ bạn giải nén):

```bash
cd duong_dan/den/kiem_tra_dem
```

**Bước 4. Tạo môi trường** (mất vài phút, cần mạng):

```bash
conda env create -f environment.yml
```

**Bước 5. Bật môi trường.** Việc này phải làm **mỗi lần** mở cửa sổ dòng lệnh mới:

```bash
conda activate kiem-tra-dem
```

Thấy chữ `(kiem-tra-dem)` ở đầu dòng lệnh là được.

**Bước 6. Kiểm tra:**

```bash
python chay_kiem_tra.py --help
```

Nếu thấy danh sách các tùy chọn như `--config`, `--diem`… là cài đặt thành công.

---

## 3. Sắp xếp thư mục

Đặt file theo đúng cấu trúc này. Các thư mục `nhan_ban_giao/`, `du_lieu_tham_chieu/` và `ket_qua/` bạn tự tạo; `ket_qua/` cũng có thể để chương trình tự tạo.

```
kiem_tra_dem/
├── README.md                     ← file này
├── TAI_LIEU_KY_THUAT.md          ← chi tiết kỹ thuật
├── chay_kiem_tra.py              ← file để chạy
├── environment.yml               ← danh sách thư viện
├── kiemtra/                      ← mã nguồn, không cần mở
│
├── cau_hinh/
│   ├── khu1.yaml                 ← cấu hình của khu 1 (mục 5)
│   └── mau_ban_giao.yaml         ← mẫu phiếu cho người lập DEM
│
├── nhan_ban_giao/                ← DEM nhận từ người lập DEM
│   └── 2026-10-10_khu1_v1/       ← mỗi lần giao một thư mục: <ngày>_<khu>_v<số>
│       ├── khu1.tif
│       └── ban_giao.yaml
│
├── du_lieu_tham_chieu/           ← CHỈ người kiểm tra giữ
│   ├── khu1_diem_kiem_tra.csv
│   ├── khu1_ranh_gioi.geojson
│   └── khu1_chieu_cao_tan.tif
│
└── ket_qua/                      ← chương trình ghi kết quả vào đây
```

Không dùng dấu tiếng Việt và khoảng trắng trong tên file, tên thư mục.

---

## 4. Chuẩn bị file

### 4.1. Người lập DEM chuẩn bị

**File `khu1.tif`.** Mở trong QGIS, chuột phải vào lớp → **Properties** → **Information**, kiểm tra:

| Kiểm tra | Phải là | Nếu sai |
| --- | --- | --- |
| CRS (hệ tọa độ) | Hệ phẳng đơn vị mét, nên dùng **EPSG:3414 (SVY21)** | QGIS: **Raster → Projections → Warp (Reproject)**, chọn EPSG:3414 |
| NoData | Có giá trị, ví dụ -9999 | Đặt NoData khi xuất file |
| Số băng (bands) | 1 | Xuất riêng băng cao độ |
| Cao độ | Hợp lý cho khu vực (vài chục đến dưới 200 m) | Kiểm lại đơn vị (mét hay feet) |

**File `ban_giao.yaml`.** Chép `cau_hinh/mau_ban_giao.yaml`, đổi tên thành `ban_giao.yaml`, mở bằng Notepad (Windows) hoặc gedit/TextEdit, điền từng dòng. Dòng `sha256` là "dấu vân tay" của file `.tif`, dùng để biết file có bị đổi sau khi giao hay không. Lấy nó bằng lệnh:

- Windows (PowerShell): `Get-FileHash khu1.tif -Algorithm SHA256`
- macOS, Linux: `sha256sum khu1.tif`

Chép chuỗi dài in ra vào dòng `sha256: "..."`.

Ví dụ phiếu đã điền:

```yaml
file: khu1.tif
sha256: "6b9e818b4142e29597f12e12ceae5f19244d0bdb9b8271ccc462feaffdf64b72"
ngay_giao: "2026-10-10"
phien_ban: v1
he_toa_do: "EPSG:3414"
he_cao_do: "EGM2008"
nodata: -9999
do_phan_giai_m: 30
nguon_va_quy_trinh: "Copernicus GLO-30, chuyển SVY21 bằng QGIS 3.x"
do_thi_xu_ly: ""
chua_xem_diem_kiem_tra: true
ghi_chu: ""
```

Sau khi giao, **không sửa** file `.tif` nữa. Muốn sửa thì giao bản mới (`v2`) trong thư mục mới.

### 4.2. Người kiểm tra chuẩn bị

| File | Nội dung | Bắt buộc |
| --- | --- | --- |
| `khu1_diem_kiem_tra.csv` | Các điểm có cao độ đo thật | **Có** |
| `khu1_ranh_gioi.geojson` | Đường bao khu vực | Nên có |
| `khu1_chieu_cao_tan.tif` | Chiều cao tán rừng (m) | Nên có |

**Bảng điểm `khu1_diem_kiem_tra.csv`** mở được bằng Excel. Dòng đầu là tên cột:

```csv
id,x,y,z_ref,nguon,co_chat_luong,tuyen,thu_tu
1,23456.7,34567.8,85.21,ICESat-2,0,T01,0
2,23460.1,34467.9,84.73,ICESat-2,0,T01,1
```

| Cột | Ý nghĩa | Bắt buộc |
| --- | --- | --- |
| `id` | Số thứ tự, không trùng | Có |
| `x`, `y` | Tọa độ, **cùng hệ với DEM** (SVY21) | Có |
| `z_ref` | Cao độ đo thật (m), **cùng hệ cao độ với DEM** | Có |
| `lop` | `trong`, `thua` hoặc `day` | Không; thiếu thì chương trình tự chia theo chiều cao tán |
| `tuyen`, `thu_tu` | Tuyến bay và thứ tự điểm trên tuyến | Không; có thì chấm thêm C4 |
| `co_chat_luong`, `nguon` | Cờ lọc, nguồn dữ liệu | Không |

Lưu bằng Excel thì chọn **CSV UTF-8**. Dùng dấu chấm cho số thập phân (`85.21`, không phải `85,21`).

**Ranh giới:** vẽ đa giác trong QGIS, đặt CRS là EPSG:3414, chuột phải → **Export → Save Features As…** → định dạng **GeoJSON**.

**Chiều cao tán:** cắt theo khu vực và đưa về EPSG:3414 bằng **Raster → Projections → Warp** trong QGIS.

**Đóng băng bảng điểm** trước khi nhận DEM: lấy mã sha256 của `khu1_diem_kiem_tra.csv` (cùng lệnh như mục 4.1), ghi vào cấu hình ở mục 5. Từ lúc đó không sửa bảng điểm nữa.

---

## 5. Điền file cấu hình

Mở `cau_hinh/khu1.yaml` bằng trình soạn thảo văn bản. Chỉ cần sửa các dòng sau; các dòng khác để nguyên.

| Dòng | Điền gì | Ví dụ |
| --- | --- | --- |
| `T` | Ngưỡng sai số (m) đã thống nhất với thầy | `T: 2.0` |
| `do_phan_giai` | Kích thước ô yêu cầu (m) | `do_phan_giai: 30` |
| `he_cao_do: diem` | Hệ cao độ của cột `z_ref` | `diem: "EGM2008"` |
| `du_lieu` | Đường dẫn tới 3 file tham chiếu | Đã điền sẵn theo mục 3 |
| `loc_diem` | Điều kiện lọc điểm (bỏ trống nếu không lọc) | `loc_diem: "co_chat_luong == 0"` |
| `kiem_chung: doc_lap` | `true` khi chắc chắn người lập DEM chưa xem điểm kiểm tra | `doc_lap: true` |
| `kiem_chung: sha256_diem` | Mã sha256 của bảng điểm (mục 4.2) | `sha256_diem: "a1b2..."` |
| `kiem_tra_thu_cong` | Điền **sau** lần chạy đầu (mục 8) | `loi_hinh_anh: 2` |

Lưu ý khi sửa file `.yaml`:
- Giữ nguyên khoảng trắng đầu dòng. Dùng dấu cách, không dùng phím Tab.
- Đường dẫn trong `du_lieu` bắt đầu bằng `../` vì được tính từ thư mục `cau_hinh/`.
- `null` nghĩa là "chưa điền".

---

## 6. Chạy chương trình

**Bước 1.** Mở cửa sổ dòng lệnh, vào thư mục chương trình và bật môi trường:

```bash
cd duong_dan/den/kiem_tra_dem
conda activate kiem-tra-dem
```

**Bước 2.** Chạy, thay tên thư mục bàn giao cho đúng:

```bash
python chay_kiem_tra.py nhan_ban_giao/2026-10-10_khu1_v1/khu1.tif --config cau_hinh/khu1.yaml
```

**Bước 3.** Chương trình in ra 6 bước:

```
[1/6] Đọc và kiểm tra DEM: khu1.tif
      mã băm DEM khớp phiếu bàn giao
[2/6] Đọc dữ liệu tham chiếu
[3/6] Lấy cao độ DEM tại điểm (nội suy song tuyến), tính sai số
      321 điểm dùng để chấm, 2 điểm bị loại (...)
[4/6] Tính độ lệch
[5/6] Chấm tiêu chí C1-C8
[6/6] Ghi kết quả
```

rồi in bảng kết quả (mục 7). Kết quả cũng được lưu trong `ket_qua/2026-10-10_khu1_v1_<ngày giờ>/`.

Muốn tự đặt tên thư mục kết quả, thêm `--ra ket_qua/ten_ban_muon`. Chương trình không ghi đè: nếu thư mục đã có, nó báo lỗi để bạn đổi tên.

**Các tùy chọn khác** (thường không cần):

| Tùy chọn | Dùng khi |
| --- | --- |
| `--diem`, `--ranh-gioi`, `--tan` | Muốn dùng file khác với file khai trong cấu hình |
| `--ban-giao` | Phiếu bàn giao không nằm cạnh file `.tif` |
| `--dem-chay-lai` | Người lập DEM đã chạy lại quy trình trên máy khác (tiêu chí C8) |
| `--T 3.0` | Thử nhanh với ngưỡng khác, không sửa cấu hình |

---

## 7. Đọc kết quả

Ví dụ dưới đây dùng dữ liệu **giả lập**, không phải kết quả thật.

### 7.1. Bảng độ lệch

```
 ĐỘ LỆCH (sai số = DEM - tham chiếu, đơn vị m)
  Phạm vi          n       ME       SD      MAE     RMSE     LE90      min      max
  toàn khu       321    3.168    3.549    3.332    4.758    8.748   -1.470   12.846
  trong          155    0.371    0.810    0.712    0.891    1.553   -1.470    2.351
  thua           113    4.088    1.941    4.088    4.526    6.944    0.288    8.547
  day             53    9.385    1.738    9.385    9.544   11.629    6.330   12.846
```

| Chữ | Nghĩa bằng lời thường |
| --- | --- |
| **n** | Số điểm dùng để tính |
| **ME** | Trung bình DEM cao hơn (+) hay thấp hơn (−) thực tế bao nhiêu mét |
| **SD** | Sai số dao động nhiều hay ít quanh mức trung bình |
| **MAE** | Trung bình mỗi điểm sai bao nhiêu mét, không tính dấu |
| **RMSE** | Con số sai số chính, phạt nặng các điểm sai nhiều. **So với T** |
| **LE90** | 90% số điểm sai không quá con số này |
| **min, max** | Điểm sai thấp nhất và cao nhất |
| **trong / thua / day** | Vùng trống / rừng thưa / rừng dày |

Cách đọc ví dụ: ở vùng trống DEM chỉ lệch khoảng 0,9 m, nhưng ở rừng dày lệch khoảng 9,5 m và luôn cao hơn thực tế (ME dương, min dương). Điều này gợi ý DEM đang bám theo mặt tán cây chứ không phải mặt đất.

### 7.2. Khoảng tin cậy và tương quan với tán

```
  toan_khu    [3.099, 6.107] m, lấy mẫu theo tuyến
 Spearman |e| ~ chiều cao tán: rho = 0.909, p = 1.5e-123, n = 321
```

- **Khoảng tin cậy:** RMSE thật nhiều khả năng nằm trong khoảng này. Nếu T nằm trong khoảng, chương trình ghi "sát ngưỡng": chưa đủ chắc để nói đạt hay không đạt.
- **Spearman rho:** gần 1 nghĩa là cây càng cao thì sai số càng lớn. Đây là bằng chứng cho giả thuyết "tán rừng gây sai số".

### 7.3. Bảng điểm

```
  Mã          Điểm  /Tối đa   Giá trị chính
  C1          0.00      /20   RMSE=4.758, LE90=8.748, r=2.379
                           -> trừ 4 điểm vì LE90 > 2T
  C2          5.00      /15   trong: RMSE=0.891 (5.0đ, n=155), ...
  ...
  C6    không chấm      /10   ...
                           -> chưa đủ để chấm, thiếu mục: 3_loi_hinh_anh, 4_mep_ghep
```

| Mã | Chấm điều gì | Tối đa |
| --- | --- | --- |
| C1 | Sai số chung (RMSE, LE90) so với T | 20 |
| C2 | Sai số riêng ở từng vùng: trống, thưa, dày | 15 |
| C3 | DEM có bị lệch đều lên hay xuống không | 10 |
| C4 | Độ dốc địa hình có đúng không | 10 |
| C5 | DEM có bị thủng lỗ (ô trống) không | 10 |
| C6 | File có lỗi kỹ thuật không (hệ tọa độ, đơn vị, sọc, mép ghép) | 10 |
| C7 | Phép kiểm tra có đáng tin không (điểm độc lập, đủ nhiều) | 15 |
| C8 | Người khác làm lại có ra cùng DEM không | 10 |

Dòng có mũi tên `->` giải thích vì sao bị trừ điểm hoặc vì sao "không chấm". **"Không chấm"** nghĩa là thiếu thông tin, không phải 0 điểm; tổng được quy đổi về thang 100 từ các tiêu chí đã chấm.

### 7.4. Xếp loại

```
 Tổng thô: 56.00 / 100   Tổng quy đổi về 100: 56.00
 Xếp loại theo điểm : Chưa đạt, dùng hạn chế
 Xếp loại chính thức: Chưa đạt, dùng hạn chế
 Kết luận ở mốc G3  : DEM chưa đạt: chuyển sang chẩn đoán (Phần II)
```

| Xếp loại | Ý nghĩa |
| --- | --- |
| **Tốt** | Đạt ngưỡng chắc chắn, kiểm chứng đáng tin, làm lại ra cùng kết quả |
| **Đạt** | Đạt ngưỡng sai số |
| **Chưa đạt, dùng hạn chế** | Dùng được ở một số vùng (ví dụ vùng trống), chưa đạt ở toàn khu |
| **Không đạt** | Sai số quá lớn |
| **CHƯA XẾP LOẠI** | Thiếu điều kiện để kết luận, ví dụ chưa xác nhận điểm kiểm tra độc lập. Xem các dòng gạch đầu dòng ngay dưới |

Khi DEM chưa đạt, việc tiếp theo là tìm nguyên nhân (Phần II trong tài liệu tiêu chí). Phần đó do người duyệt làm, chương trình không chấm.

### 7.5. File kết quả

Trong thư mục `ket_qua/<tên>/`:

| File | Nội dung | Gửi người lập DEM? |
| --- | --- | --- |
| `ket_qua.json` | Toàn bộ số liệu và điểm | Có |
| `ban_ghi_chay.json` | Ngày giờ, phiên bản, dấu vân tay các file đã dùng | Có |
| `sai_so_tung_diem.csv` | Sai số từng điểm, kèm tọa độ và cao độ tham chiếu | **Không**, trước mốc G3 |

`sai_so_tung_diem.csv` mở được bằng Excel hoặc kéo vào QGIS (cột `x`, `y`, EPSG:3414) để xem điểm nào sai nhiều nằm ở đâu.

---

## 8. Sau khi chạy

1. **Xem DEM bằng mắt.** Trong QGIS, tạo bản đồ bóng đổ: **Raster → Analysis → Hillshade**. Tìm sọc, bậc thang, hố lạ, chỗ ghép bị lệch.
2. **Điền điểm thủ công** vào `cau_hinh/khu1.yaml`:
   ```yaml
   kiem_tra_thu_cong:
     loi_hinh_anh: 2   # 2 = không thấy lỗi, 1 = có lỗi nhỏ, 0 = lỗi rõ
     mep_ghep: 2       # 2 = không lệch hoặc không có mép ghép, 1 = lệch nhỏ, 0 = lệch rõ
   ```
3. **Chạy lại** lệnh ở mục 6 (kết quả vào thư mục mới).
4. **Viết `nhan_xet.md`** trong thư mục kết quả: vài dòng về điều thấy được, điểm nào cần sửa ở bản sau.
5. **Gửi người lập DEM** `ket_qua.json` và `nhan_xet.md`.

---

## 9. Khi chương trình báo lỗi

Chương trình dừng và in dòng `[LỖI ĐẦU VÀO] ...`. Nó không tự sửa file.

| Thông báo | Nguyên nhân | Cách sửa |
| --- | --- | --- |
| `conda: command not found` hoặc `'conda' is not recognized` | Chưa cài Conda hoặc mở sai cửa sổ | Dùng Miniforge Prompt (Windows); cài lại Conda |
| `ModuleNotFoundError: No module named ...` | Chưa bật môi trường | Chạy `conda activate kiem-tra-dem` |
| `Không thấy file: ...` | Sai đường dẫn hoặc tên file | Kiểm tra tên file, thư mục đang đứng (`cd`) |
| `không khai hệ quy chiếu (EPSG)` | File `.tif` thiếu thông tin tọa độ | Người lập DEM gán CRS rồi xuất lại |
| `ở hệ địa lý EPSG:4326` | DEM ở kinh độ, vĩ độ | Người lập DEM chuyển sang EPSG:3414 (mục 4.1) |
| `Mã băm DEM không khớp phiếu bàn giao` | File bị đổi sau khi giao, hoặc chép sai mã | Hỏi lại người lập DEM; lấy lại mã sha256 |
| `thiếu cột ['z_ref']` | Bảng điểm đặt tên cột khác | Đổi tên cột trong Excel, hoặc khai mục `cot:` trong cấu hình |
| `Dưới 2 điểm hợp lệ sau khi lấy mẫu` | Tọa độ điểm khác hệ với DEM, hoặc điểm nằm ngoài DEM | Kiểm tra cột `x`, `y` đã ở SVY21 chưa |
| `Ranh giới không phủ ô nào của DEM` | Ranh giới khác hệ tọa độ | Xuất lại ranh giới với EPSG:3414 |
| `Thư mục kết quả đã tồn tại` | Trùng tên thư mục `--ra` | Đặt tên khác |
| `file .yaml sai cú pháp` | Thụt dòng sai, dùng Tab, thiếu dấu `:` | Sửa file `.yaml`, chỉ dùng dấu cách |
| `[LƯU Ý] phiếu bàn giao chưa có sha256` | Phiếu chưa điền mã | Không dừng, nhưng nên yêu cầu bổ sung |

---

## 10. Câu hỏi thường gặp

**Tôi chỉ có file `.tif`, chạy được không?**
Không. Phải có bảng điểm tham chiếu (`khu1_diem_kiem_tra.csv`), vì chương trình chấm bằng cách so DEM với cao độ đo thật.

**Tại sao một số tiêu chí ghi "không chấm"?**
Thiếu thông tin: C4 cần khai `T_doc` và có cột tuyến; C6 cần điền mục thủ công; C8 cần DEM chạy lại. Tổng vẫn được tính trên các tiêu chí còn lại.

**Tại sao "CHƯA XẾP LOẠI" dù điểm cao?**
Thường do chưa điền `doc_lap: true` hoặc phát hiện lệch ở vùng trống (nghi lỗi hệ cao độ). Đọc các dòng ngay dưới "Xếp loại chính thức".

**Đổi ngưỡng T thì có phải sửa code không?**
Không. Sửa dòng `T:` trong `cau_hinh/khu1.yaml`. Nhưng T phải chốt **trước** khi xem kết quả, không đổi sau đó cho đẹp số.

**Chấm khu 2 thì làm gì?**
Chép `cau_hinh/khu1.yaml` thành `cau_hinh/khu2.yaml`, sửa đường dẫn trong `du_lieu`, rồi chạy với `--config cau_hinh/khu2.yaml`.

**Chạy hai lần có ra cùng kết quả không?**
Có, với cùng file và cùng cấu hình. Khoảng tin cậy dùng số ngẫu nhiên nhưng đã cố định (`seed: 42`).

**Có cần biết lập trình không?**
Không. Chỉ cần gõ đúng các lệnh ở mục 2 và 6, và sửa file `.yaml` bằng trình soạn thảo văn bản.
