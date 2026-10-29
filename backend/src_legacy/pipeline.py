"""
端到端流水线：盖章处裁列 → 印章检测 → 单元切分 → 盖法分类 → 四角 OCR。

用法：
  python src/pipeline.py assets/sample_page.png
  python src/pipeline.py assets/sample_page.png --show
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digit_ocr import recognize_corners  # noqa: E402
from orientation import match_orientation  # noqa: E402
from recognize import (  # noqa: E402
    classify_group,
    cluster_nearby,
    corner_rois,
    find_components,
    group_bbox,
    ink_density,
    mask_blue,
    mask_yellow,
    merge_groups_for_pair,
    split_overlapping_blob,
)
from seal_methods import CornerDigits  # noqa: E402
from table_cells import (  # noqa: E402
    StampCell,
    cells_from_groups,
    draw_cells,
    estimate_stamp_column,
    estimate_table_top,
)


@dataclass
class StampResult:
    row: int
    col: int
    method_id: int
    method_name: str
    confidence: float
    zhi: int
    xing: int
    corner_digits: Dict[str, Optional[int]]
    bbox: Tuple[int, int, int, int]
    cell_bbox: Tuple[int, int, int, int]
    orientation: Optional[int] = None  # 单枚知章朝向 0/180


@dataclass
class PageResult:
    stamp_column: Tuple[int, int]
    table_top: int
    cells: int
    stamps: List[StampResult] = field(default_factory=list)


def _expand_comps(comps: List[Dict]) -> List[Dict]:
    if not comps:
        return []
    areas = sorted(c["area"] for c in comps)
    median = float(np.percentile(areas, 35))
    out: List[Dict] = []
    for c in comps:
        out.extend(split_overlapping_blob(c, median))
    return out


def detect_seal_groups(
    img: np.ndarray,
) -> Tuple[List[List[Dict]], List[List[Dict]], np.ndarray, np.ndarray]:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    blue = mask_blue(hsv)
    yellow = mask_yellow(hsv)
    # 知章：要求框内有足够蓝墨；行章：要求更圆、填充足够
    zhi_raw = find_components(blue, min_area=700, min_fill=0.12, min_circularity=0.04)
    xing_raw = find_components(
        yellow, min_area=500, min_fill=0.12, min_circularity=0.20
    )
    zhi = _expand_comps(zhi_raw)
    # 行章一般不粘连拆分；碎环已在掩膜里闭合
    xing = xing_raw
    return cluster_nearby(zhi, dist_ratio=0.80), cluster_nearby(xing, dist_ratio=0.75), blue, yellow


def is_valid_detection(
    bgr: np.ndarray,
    blue: np.ndarray,
    yellow: np.ndarray,
    zg: List[Dict],
    xg: List[Dict],
    bb: Tuple[int, int, int, int],
) -> bool:
    """拒绝空白格误检：框内几乎无蓝/黄墨。"""
    x, y, w, h = bb
    dens_b = ink_density(blue, bb) if zg else 0.0
    dens_y = ink_density(yellow, bb) if xg else 0.0

    # 过大框必须有足够墨迹（空白格常见）
    if w * h > 180 * 180 and max(dens_b, dens_y) < 0.10:
        return False
    if zg and dens_b < 0.09:
        return False
    if xg and not zg and dens_y < 0.10:
        return False
    if dens_b + dens_y < 0.07:
        return False

    # 单枚知章：模板相关过低视为噪声（阴影/污点）
    if len(zg) == 1 and not xg:
        from orientation import _crop_ink, _zhi_templates

        patch = _crop_ink(bgr, bb)
        temps = _zhi_templates()
        if patch is None or not temps:
            return dens_b >= 0.15
        a = patch.astype(np.float32)
        a = (a - a.mean()) / (a.std() + 1e-6)
        best = -1.0
        for _, t in temps:
            b = t.astype(np.float32)
            b = (b - b.mean()) / (b.std() + 1e-6)
            best = max(best, float((a * b).mean()))
        if best < 0.12:
            return False
    return True


def _group_as_bbox_dict(group: List[Dict]) -> Optional[Dict]:
    bb = group_bbox(group)
    if not bb:
        return None
    x, y, w, h = bb
    return {"x": x, "y": y, "w": w, "h": h, "cx": x + w / 2, "cy": y + h / 2}


def run_page(image_path: Path) -> PageResult:
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(image_path)

    H, W = img.shape[:2]
    x0, x1 = estimate_stamp_column(img)
    top = estimate_table_top(img, x0)

    # 屏蔽时间列与表头，减少干扰
    work = img.copy()
    work[:, : max(0, x0 - 2)] = 255
    work[:top, :] = 255

    zhi_groups, xing_groups, blue_m, yellow_m = detect_seal_groups(work)
    pairs = merge_groups_for_pair(zhi_groups, xing_groups)

    # 用每个 pair 的联合 bbox 做单元切分
    unit_dicts: List[Dict] = []
    pair_meta = []
    for zg, xg in pairs:
        bb = group_bbox(zg) or group_bbox(xg)
        if not bb:
            continue
        if not is_valid_detection(work, blue_m, yellow_m, zg, xg, bb):
            continue
        mid, name, conf = classify_group(zg, xg, bgr=img)
        if mid == 0:
            continue
        x, y, w, h = bb
        unit_dicts.append({"x": x, "y": y, "w": w, "h": h, "cx": x + w / 2, "cy": y + h / 2})
        pair_meta.append((zg, xg, mid, name, conf, bb))

    cells = cells_from_groups(unit_dicts, (H, W), x0, x1, pad=24)

    def _digits_for(zg, bb):
        if not zg:
            return {"左上": None, "右上": None, "左下": None, "右下": None}
        # 叠盖组：数字在整组外接矩形的内角；单章则在单章内角
        return recognize_corners(img, corner_rois(bb, pad=26), bbox=bb)

    # 将 pair 与 cell 按中心最近匹配
    results: List[StampResult] = []
    used_pairs = set()
    for cell in cells:
        cx = cell.bbox[0] + cell.bbox[2] / 2
        cy = cell.bbox[1] + cell.bbox[3] / 2
        best_i, best_d = None, 1e18
        for i, meta in enumerate(pair_meta):
            if i in used_pairs:
                continue
            bx = meta[5]
            pcx, pcy = bx[0] + bx[2] / 2, bx[1] + bx[3] / 2
            d = (pcx - cx) ** 2 + (pcy - cy) ** 2
            if d < best_d:
                best_d, best_i = d, i
        if best_i is None:
            continue
        used_pairs.add(best_i)
        zg, xg, mid, name, conf, bb = pair_meta[best_i]
        ori = None
        if len(zg) == 1:
            ori, _ = match_orientation(img, bb)

        results.append(
            StampResult(
                row=cell.row,
                col=cell.col,
                method_id=mid,
                method_name=name,
                confidence=round(conf, 3),
                zhi=len(zg),
                xing=len(xg),
                orientation=ori,
                corner_digits=_digits_for(zg, bb),
                bbox=bb,
                cell_bbox=cell.pad_bbox,
            )
        )

    # 未匹配到 cell 的 pair 也输出
    for i, meta in enumerate(pair_meta):
        if i in used_pairs:
            continue
        zg, xg, mid, name, conf, bb = meta
        ori = None
        if len(zg) == 1:
            ori, _ = match_orientation(img, bb)
        results.append(
            StampResult(
                row=-1,
                col=-1,
                method_id=mid,
                method_name=name,
                confidence=round(conf, 3),
                zhi=len(zg),
                xing=len(xg),
                corner_digits=_digits_for(zg, bb),
                bbox=bb,
                cell_bbox=bb,
                orientation=ori,
            )
        )

    results.sort(key=lambda r: (r.row if r.row >= 0 else 999, r.col, r.bbox[1], r.bbox[0]))
    return PageResult(
        stamp_column=(x0, x1),
        table_top=top,
        cells=len(cells),
        stamps=results,
    )


def draw_page(img: np.ndarray, page: PageResult) -> np.ndarray:
    out = img.copy()
    x0, x1 = page.stamp_column
    cv2.line(out, (x0, 0), (x0, out.shape[0]), (80, 80, 80), 1)
    cv2.line(out, (0, page.table_top), (out.shape[1], page.table_top), (80, 80, 80), 1)

    fake_cells = [
        StampCell(r.row, r.col, r.bbox, r.cell_bbox) for r in page.stamps if r.row >= 0
    ]
    out = draw_cells(out, fake_cells)

    for r in page.stamps:
        x, y, w, h = r.bbox
        color = (30, 90, 200) if r.zhi else (0, 170, 220)
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        dig = r.corner_digits
        dig_s = "".join(
            str(dig[k]) if dig.get(k) is not None else "."
            for k in ("左上", "右上", "左下", "右下")
        )
        label = f"{r.method_id}:{r.method_name} [{dig_s}]"
        cv2.putText(
            out, label, (x, max(16, y - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA,
        )
        if r.zhi:
            for roi in corner_rois(r.bbox, pad=26).values():
                rx, ry, rw, rh = roi
                cv2.rectangle(out, (rx, ry), (rx + rw, ry + rh), (40, 60, 200), 1)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="印章识别端到端流水线")
    parser.add_argument("image", type=Path)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "output" / "result.jpg")
    parser.add_argument("--json", type=Path, default=ROOT / "output" / "result.json")
    args = parser.parse_args()

    page = run_page(args.image)
    payload = {
        "stamp_column": list(page.stamp_column),
        "table_top": page.table_top,
        "cells": page.cells,
        "stamps": [asdict(s) for s in page.stamps],
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n单元 {page.cells} 个，识别 {len(page.stamps)} 组 → {args.json}")

    if args.show:
        img = cv2.imread(str(args.image))
        vis = draw_page(img, page)
        cv2.imwrite(str(args.out), vis)
        print(f"结果图 → {args.out}")


if __name__ == "__main__":
    main()
