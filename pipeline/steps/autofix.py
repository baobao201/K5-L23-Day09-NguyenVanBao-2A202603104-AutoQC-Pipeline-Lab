"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, ROOT, parse_yolo_line

DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _clip(text):
    cls, x, y, w, h = parse_yolo_line(text)
    left, right = max(0.0, x - w / 2), min(1.0, x + w / 2)
    top, bottom = max(0.0, y - h / 2), min(1.0, y + h / 2)
    if left >= right or top >= bottom:
        return None
    return f"{cls} {(left + right) / 2} {(top + bottom) / 2} {right - left} {bottom - top}"


def fix(ds, issues, cfg):
    if ds.root.resolve().is_relative_to((ROOT / "data/raw").resolve()):
        raise ValueError("autofix cần bản sao làm việc của dữ liệu")

    remove = set()
    needs_label = set()
    line_issues = defaultdict(lambda: defaultdict(set))
    rename = False
    for issue in issues:
        if issue.severity != ERROR:
            continue
        if issue.code in REMOVE_CODES or issue.code.startswith("DUP_IMAGE_"):
            remove.add(issue.image)
        elif issue.code == "BAD_CLASS_NAME":
            rename = True
        elif issue.code == "MISSING_LABEL_FILE":
            needs_label.add(issue.image)
        elif issue.line is not None and (issue.code in DROP_CODES or issue.code == "BOX_OUT_OF_IMAGE"):
            line_issues[issue.image][issue.line].add(issue.code)

    fixes = []
    if remove:
        paths_by_stem = defaultdict(list)
        for path in ds.image_files():
            if path.stem in remove:
                paths_by_stem[path.stem].append(path)
        for stem in sorted(remove):
            paths = paths_by_stem[stem]
            label_path = ds.label_path(stem)
            if label_path.exists():
                paths.append(label_path)
            if paths:
                for path in paths:
                    path.unlink()
                fixes.append(dict(image=stem, line=None, action="remove_image",
                                  before=", ".join(path.name for path in paths), after=""))

    if rename:
        data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) if ds.yaml_path.exists() else {}
        data = data or {}
        before = data.get("names")
        classes = cfg["classes"]
        if before != classes and before != dict(enumerate(classes)):
            data["names"] = classes
            ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                                    encoding="utf-8", newline="\n")
            fixes.append(dict(image="data.yaml", line=None, action="rename_classes",
                              before=repr(before), after=repr(classes)))

    for stem in sorted(needs_label - remove):
        if not ds.label_path(stem).exists():
            fixes.append(dict(image=stem, line=None, action="needs_label",
                              before="(không có file)", after="chuyển người gán"))

    for stem in sorted(line_issues.keys() - remove):
        path = ds.label_path(stem)
        if not path.exists():
            continue
        kept = []
        changes = []
        for line, before in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            codes = line_issues[stem].get(line)
            if not codes or not before.strip():
                kept.append(before)
                continue
            after = None if DROP_CODES.intersection(codes) else _clip(before)
            if after is not None:
                kept.append(after)
            if after != before:
                changes.append(dict(image=stem, line=line, action="drop_line" if after is None else "clip_box",
                                    before=before, after=after or ""))
        if changes:
            path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8", newline="\n")
            fixes.extend(changes)
    return fixes
