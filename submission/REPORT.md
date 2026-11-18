# Báo cáo Day 09 — Nguyễn Văn Bảo, 2A202603104

## 1. Kết luận

**Hold (mã thoát 10).** Cửa vào nhận **205/224 ảnh** và loại 19 ảnh. Sau khi duyệt mô phỏng 80 ảnh, còn **0 lỗi bắt buộc** và **38/205 ảnh chưa duyệt còn cảnh báo (18,54%)**, vượt ngưỡng Hold 10%. Pipeline xuất bản nháp `clean_v1` gồm 205 ảnh theo manifest. [Tóm tắt pipeline](reports/08_summary.json) · [Manifest](export/clean_v1/manifest.json)

## 2. Lỗi và phân việc

Bảng đếm theo v1. Mẫu số là 224 ảnh ở cửa vào và 205 ảnh ở bước QC sau cửa vào. Một ảnh có thể mang nhiều cờ. Hai mã cấp dataset được đếm theo số mục.

| Mã lỗi | Số dòng cờ | Số ảnh | Xử lý |
|---|---:|---:|---|
| `BAD_SIZE` | 3 | 3 | Máy loại ảnh có cạnh ngắn dưới 250 px |
| `CORRUPT_IMAGE` | 2 | 2 | Máy loại ảnh lỗi giải mã |
| `DUP_IMAGE_EXACT` | 8 | 8 | Máy loại bản trùng byte |
| `DUP_IMAGE_NEAR` | 2 | 2 | Máy loại bản trùng theo pHash |
| `LEAK_TEST` | 4 | 4 | Máy loại ảnh trùng kho đánh giá |
| `BAD_CLASS_ID` | 6 | 6 | Máy bỏ dòng có ID ngoài danh sách |
| `BAD_CLASS_NAME` | 2 | — | Máy chuẩn hóa `names` trong một file YAML |
| `BAD_FORMAT` | 3 | 3 | Máy bỏ dòng sai định dạng |
| `BOX_OUT_OF_IMAGE` | 8 | 8 | Máy cắt box theo mép ảnh |
| `BOX_ZERO` | 4 | 4 | Máy bỏ box có cạnh bằng 0 |
| `DUP_BOX` | 7 | 7 | Máy bỏ dòng box trùng xuất hiện sau |
| `MISSING_LABEL_FILE` | 6 | 6 | Người gán nhãn cho ảnh thiếu file |
| `BOX_HUGE` | 3 | 3 | Người kiểm tra box chiếm gần hết ảnh |
| `BOX_TINY` | 6 | 4 | Người đối chiếu vật nhỏ với quy tắc gán nhãn |
| `CLASS_RARE` | 4 | — | Kiểm tra thống kê toàn lô sau khi máy bỏ các ID lạ |
| `EMPTY_LABEL` | 12 | 12 | Người xác định ảnh nền hay thiếu box |
| `POSSIBLE_FALSE_POS` | 29 | 27 | Người xác minh box có thực sự thừa |
| `POSSIBLE_LOOSE_BOX` | 28 | 24 | Người đối chiếu mép box với vật thể |
| `POSSIBLE_MISSING` | 53 | 52 | Người xác minh vật chưa có box |
| `POSSIBLE_WRONG_CLASS` | 18 | 18 | Người xác nhận lớp thực tế |

`03_fixes.csv` ghi 20 lượt bỏ dòng, 8 lượt cắt box, 1 lượt chuẩn hóa YAML và 6 lượt chuyển người gán. Hàng đợi cộng trọng số theo từng cờ, tăng điểm theo độ tin cậy của dự đoán khi có, rồi xếp giảm dần. `img_0020` đứng đầu với 11,524 điểm do cộng một lần bỏ dòng, một cờ nghi nhầm lớp và một cờ nghi thiếu box. Sáu ảnh thiếu file nhãn xếp ngay sau, mỗi ảnh 10 điểm. Người duyệt mô phỏng xem **80/125 ảnh** trong hàng đợi, phủ **94/123 cờ ngữ nghĩa v2 trên 74/103 ảnh** có cờ loại này. [Lỗi v1](reports/02_error_list_v1.csv) · [Nhật ký sửa](reports/03_fixes.csv) · [Hàng đợi](reports/05_review_queue.csv) · [Nhật ký duyệt](reports/06_review_log.csv)

## 3. Calibration

| Tham số | Khởi đầu → đã chọn | Precision / Recall trước → sau | Lý do |
|---|---|---|---|
| `duplicates.phash_dist` | 2 → **4** | Trùng gần 100% / 50% → 100% / 66,7%. Trùng byte giữ 100% / 100% | Bắt thêm 1 ca trên 6 ca trùng gần, với 0 cờ nhầm trong calib. Các mức 6–14 có cùng kết quả. Giữ 4 để hạn chế gộp nhầm khi loại ảnh tự động. |
| `second_opinion.conf` | 0,25 → **0,60** | Thiếu box 50% / 100% → 57,1% / 100%. Nhầm lớp 55,6% / 83,3% → 62,5% / 83,3%. Box lỏng 28,6% / 40% → 20% / 20%. Box nghi thừa giữ 31,3% / 100%. | Ưu tiên giữ đủ 8 ca thiếu box và 5/6 ca nhầm lớp đã phát hiện. Hai nhóm này giảm tổng cộng 3 cờ nhầm, đổi lại mất thêm 1 ca box lỏng. Cờ nghi thừa dùng ngưỡng riêng `fp_conf`. |

Precision 100% của trùng gần ở ngưỡng 4 chỉ dựa trên **4 cờ đúng** trong 39 ảnh calib. Trên raw, cả ngưỡng 2 và 4 đều loại **19/224 ảnh**, nên lợi ích trên calib chưa xuất hiện trên lô này. Đối chiếu bằng mắt hai cặp trùng gần được báo (`img_0042`–`img_0076` và `img_0037`–`img_0143`) cho thấy cùng cảnh ở hai độ phân giải. [Bảng sweep](calibration/calibration_report.md) · [Kết quả cửa vào](reports/01_intake.csv)

## 4. Cửa chặn và điểm mù

- Chạy `python -m pipeline.run --budget 0 --work work/run_nb --reports work/rep_nb --export-dir work/exp_nb` cho **Rework**, mã thoát **20**, với **6 ảnh thiếu file nhãn trên 205 ảnh**. Thư mục xuất `work/exp_nb/clean_v1` không được tạo.
- Trên calib, ngưỡng đã chọn bỏ sót **4/5 ca box lỏng**. Box vẫn nằm trong ảnh và có thể đạt IoU đủ cao với model dù mép box dư nền, nên cần kiểm tra hình học bằng mắt.
- Trên calib, pHash ở ngưỡng 4 bỏ sót **2/6 ca trùng gần**. Một ảnh đã biến đổi có thể vẫn là bản sao nhưng vượt khoảng cách Hamming cho phép. [Calibration](calibration/calibration_report.md)
- Quan sát ảnh raw cho thấy `img_0001` có hai box đỏ gần chồng khít trên người bên trái và thiếu box cho người đứng bên phải. `img_0030` có box dòng 9 cắt qua mép ảnh. Đối chiếu v1 xác nhận một cờ lặp, một cờ thiếu box (conf 0,9458) và một box tràn 2,30% cạnh ảnh. [Lỗi v1](reports/02_error_list_v1.csv)

## 5. Train raw và clean

Chạy YOLO26n trong `.venv` trên GTX 1650 4 GB với Ultralytics 8.4.214 và PyTorch 2.7.1+cu126. Cả hai biến thể dùng cùng trọng số khởi tạo, 20 epoch, seed 0 và 1, ảnh 416 px, batch 8 và cùng tập validation 40 ảnh. Script chọn checkpoint theo validation rồi đo trên cùng 100 ảnh test. Ultralytics tự loại 11 ảnh hoặc nhãn lỗi trong `raw`, nên 224 ảnh đầu vào tương ứng 213 ảnh thực dùng. `clean` dùng đủ 205 ảnh.

| Biến thể | Ảnh train đầu vào | Số seed | mAP50 (TB ± độ lệch) | mAP50–95 | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| raw | 224 | 2 | 0,577 ± 0,001 | 0,392 ± 0,005 | 0,708 ± 0,023 | 0,494 ± 0,017 |
| clean | 205 | 2 | 0,622 ± 0,016 | 0,437 ± 0,007 | 0,773 ± 0,002 | 0,506 ± 0,014 |

**mAP50 tăng 4,46 điểm phần trăm** với `clean` trên tập test này. Hai chênh lệch theo seed là +5,71 và +3,21 điểm phần trăm. Mức tăng trung bình lớn hơn độ lệch chuẩn giữa seed của cả `raw` (0,13 điểm phần trăm) và `clean` (1,64 điểm phần trăm). Kết quả nhất quán trong hai seed đã chạy. Cần thêm seed và tập test độc lập để kiểm tra khả năng tái lập. [Kết quả do script sinh](results/comparison.md)

- **Ảnh trùng với tập test có thể làm điểm `raw` cao hơn.** Đối chiếu cửa vào với tập ảnh loader thực dùng cho thấy 4/100 ảnh test có bản gần trùng trong `raw` (pHash cách 0–2 bit), cả bốn đã bị loại khỏi `clean`. Có thể tách kết quả theo nhóm trùng và đánh giá lại trên tập test độc lập.
- **Thay đổi thành phần ảnh và thay đổi nhãn đều có thể góp vào chênh lệch.** Loader dùng 213 ảnh `raw` so với 205 ảnh `clean`, đồng thời pipeline đã sửa cú pháp và thay nhãn cho 80 ảnh duyệt mô phỏng. Để đo riêng tác động của nhãn, có thể huấn luyện hai biến thể trên cùng tập ảnh hợp lệ, loại bản trùng và chỉ thay nhãn. [Nhật ký sửa](reports/03_fixes.csv) · [Nhật ký duyệt](reports/06_review_log.csv)

## 6. Quyết định và ghi chú AI

Giữ **Hold**. Để chuyển sang Release với mẫu số 205 ảnh, cần giữ 0 lỗi bắt buộc và xử lý đủ để hạ số ảnh chưa duyệt còn cảnh báo từ 38 xuống tối đa 20, tức giảm ít nhất 18 ảnh. Ưu tiên xem tiếp các cờ ngữ nghĩa theo hàng đợi trong đợt duyệt sau. [Lỗi v3](reports/07_error_list_v3.txt)

- **Prompt chính.** Đọc docstring và test của bốn module để xử lý nhãn YOLO 5 cột `id cx cy w h` và dự đoán có độ tin cậy. Dùng ngưỡng cấu hình, giữ số dòng gốc trong `Issue`, ghi nhật ký trước/sau và trả quyết định gate. Chỉ sửa nhãn trên bản sao làm việc.
- **Cách kiểm.** Chạy 79 test trong `.venv`, kiểm ca có hai lỗi cùng dòng, dòng trống và ảnh có nhiều dự đoán, đối chiếu lỗi chèn trên calib, so hai lần chạy và thử chặn xuất bằng ngân sách 0.
- **Một lần AI sai.** So sánh trực tiếp bằng số thực đã báo tràn cho dòng `0 .952 .5 .1 .2` dù mép chỉ vượt đúng 0,002. Đã giới hạn bù sai số ở một ULP tại 1,0 và kiểm lại với trường hợp bằng ngưỡng và vượt ngưỡng.
