"""
印章识别原型：颜色分离 → 形状检测 → 盖法粗分类 → 四角数字 ROI。

用法：
  python src/recognize.py assets/sample_page.png
  python src/recognize.py assets/sample_page.png --show
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from seal_methods import METHODS, CornerDigits, DetectedStamp  # noqa: E402


def _empty_mask(img: np.ndarray) -> np.ndarray:
    return np.zeros(img.shape[:2], dtype=np.uint8)


def mask_blue(hsv: np.ndarray) -> np.ndarray:
    """知章蓝色墨水（收紧阈值，避免扫描纸张偏色连成整页）。"""
    lower = np.array([100, 80, 60])
    upper = np.array([125, 255, 230])
    mask = cv2.inRange(hsv, lower, upper)
    open_k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_k, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_k, iterations=2)
    return mask


def mask_yellow(hsv: np.ndarray) -> np.ndarray:
    """行章黄色墨水（先闭运算把碎环粘回整圆）。"""
    lower = np.array([12, 40, 80])
    upper = np.array([48, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_k, iterations=1)
    return mask


def find_components(
    mask: np.ndarray,
    min_area: int = 400,
    max_area_ratio: float = 0.08,
    min_fill: float = 0.10,
    min_circularity: float = 0.0,
) -> List[Dict]:
    """轮廓 → 外接矩形；按面积/填充率过滤空白误检。"""
    H, W = mask.shape[:2]
    max_area = H * W * max_area_ratio
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    comps = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area or area > max_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        aspect = w / max(h, 1)
        if aspect < 0.45 or aspect > 2.4:
            continue
        # 框内墨迹占比：空白格/阴影常 < 0.08
        roi = mask[y : y + h, x : x + w]
        fill = float((roi > 0).mean()) if roi.size else 0.0
        if fill < min_fill:
            continue
        peri = cv2.arcLength(c, True)
        circularity = 4 * np.pi * area / max(peri**2, 1)
        if circularity < min_circularity:
            continue
        # 过稀的细长噪声（表格线残留）
        if circularity < 0.05 and fill < 0.15:
            continue
        comps.append(
            {
                "x": int(x),
                "y": int(y),
                "w": int(w),
                "h": int(h),
                "area": int(area),
                "cx": float(x + w / 2),
                "cy": float(y + h / 2),
                "aspect": float(aspect),
                "circularity": float(circularity),
                "fill": fill,
            }
        )
    return comps


def ink_density(
    mask: np.ndarray, bbox: Tuple[int, int, int, int]
) -> float:
    x, y, w, h = bbox
    H, W = mask.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    roi = mask[y0:y1, x0:x1]
    return float((roi > 0).mean()) if roi.size else 0.0


def cluster_nearby(comps: List[Dict], dist_ratio: float = 0.85) -> List[List[Dict]]:
    """
    按中心距离聚类，得到叠盖组。
    dist_ratio < 1：只有真正叠盖/紧挨的章会进同一组；同行并列章会分开。
    """
    if not comps:
        return []
    sizes = [max(c["w"], c["h"]) for c in comps]
    avg = float(np.mean(sizes)) if sizes else 50.0
    thresh = avg * dist_ratio

    used = [False] * len(comps)
    groups: List[List[Dict]] = []
    for i, c in enumerate(comps):
        if used[i]:
            continue
        group = [c]
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j, d in enumerate(comps):
                if used[j]:
                    continue
                for g in group:
                    dist = np.hypot(g["cx"] - d["cx"], g["cy"] - d["cy"])
                    if dist < thresh:
                        group.append(d)
                        used[j] = True
                        changed = True
                        break
        groups.append(group)
    return groups


def split_overlapping_blob(comp: Dict, median_area: float) -> List[Dict]:
    """
    单连通域面积过大时，按面积估计枚数，并沿主轴方向虚拟拆点。
    仅在填充率足够、面积显著大于单章时拆分，避免空白/噪声被拆成多枚。
    """
    fill = float(comp.get("fill", 0.2))
    if fill < 0.18:
        return [comp]

    ratio = comp["area"] / max(median_area, 1)
    # 需要明显大于 2 倍才认为叠盖粘连，且最多按几何估计 3 枚
    if ratio < 2.0:
        return [comp]
    # 用外接框相对单章尺寸估计，避免面积噪声拆出过多
    side = max(comp["w"], comp["h"])
    unit = max(median_area ** 0.5, 40.0)
    n_geom = int(round((side / unit) ** 1.3))
    n = max(1, min(3, int(round(ratio)), n_geom))
    if n == 1:
        return [comp]

    out = []
    w, h = comp["w"], comp["h"]
    cx, cy = comp["cx"], comp["cy"]
    if n == 2:
        offsets = [(-0.22 * w, -0.08 * h), (0.22 * w, 0.08 * h)]
    else:
        offsets = [(-0.25 * w, 0.18 * h), (0.25 * w, 0.18 * h), (0.0, -0.22 * h)]

    for k, (dx, dy) in enumerate(offsets):
        cc = dict(comp)
        cc["cx"] = cx + dx
        cc["cy"] = cy + dy
        cc["split_index"] = k
        cc["w"] = max(16, int(w / n + 6))
        cc["h"] = max(16, int(h / max(n - 1, 1) + 6))
        cc["x"] = int(cc["cx"] - cc["w"] / 2)
        cc["y"] = int(cc["cy"] - cc["h"] / 2)
        cc["area"] = int(comp["area"] / n)
        out.append(cc)
    return out


def classify_group(
    zhi_group: List[Dict],
    xing_group: List[Dict],
    bgr: Optional[np.ndarray] = None,
) -> Tuple[int, str, float]:
    """
    盖法分类：数量启发式 + 知章朝向（正向/引导）。
    """
    from orientation import classify_zhi_layout, orientations_in_group

    nz, nx = len(zhi_group), len(xing_group)

    # 知行对章系列
    if nz and nx:
        if nz == 1 and nx == 1:
            return 9, "知行对章", 0.75
        if nz == 2 and nx == 2:
            return 10, "知行对章二叠章", 0.72
        if nz >= 3 and nx >= 3:
            return 11, "知行对章三叠章", 0.70
        return 9, "知行对章(近似)", 0.55

    # 纯行章
    if nx and not nz:
        if nx == 1:
            return 6, "行章", 0.85
        if nx == 2:
            return 7, "行章二叠章", 0.80
        return 8, "行章三叠章", 0.78

    # 纯知章：用朝向区分正向 / 引导 / 改进
    if nz >= 1 and bgr is not None:
        degs = orientations_in_group(bgr, zhi_group)
        return classify_zhi_layout(zhi_group, degs)

    if nz == 1:
        return 1, "正向章（知章）", 0.70
    if nz == 2:
        return 4, "知章二叠章", 0.68
    if nz >= 3:
        return 5, "知章三叠章", 0.68

    return 0, "未知", 0.0


def group_bbox(comps: List[Dict]) -> Optional[Tuple[int, int, int, int]]:
    if not comps:
        return None
    x0 = min(c["x"] for c in comps)
    y0 = min(c["y"] for c in comps)
    x1 = max(c["x"] + c["w"] for c in comps)
    y1 = max(c["y"] + c["h"] for c in comps)
    return x0, y0, x1 - x0, y1 - y0


def corner_rois(
    bbox: Tuple[int, int, int, int], pad: int = 28
) -> Dict[str, Tuple[int, int, int, int]]:
    """
    方章四角数字 ROI。
    数字写在方章内侧四角（斜线旁），取内角小窗；pad 兼容旧参数作边长比例参考。
    """
    x, y, w, h = bbox
    # 内角窗口：约章边 45%，把角上数字完整罩住
    s = int(min(max(w, h) * 0.45, 56))
    s = max(18, min(s, w // 2 - 1, h // 2 - 1))
    return {
        "左上": (x + 2, y + 2, s, s),
        "右上": (x + w - s - 2, y + 2, s, s),
        "左下": (x + 2, y + h - s - 2, s, s),
        "右下": (x + w - s - 2, y + h - s - 2, s, s),
    }


def merge_groups_for_pair(
    zhi_groups: List[List[Dict]], xing_groups: List[List[Dict]]
) -> List[Tuple[List[Dict], List[Dict]]]:
    """将空间邻近的知章组与行章组配对。"""
    pairs: List[Tuple[List[Dict], List[Dict]]] = []
    used_x = set()

    for zg in zhi_groups:
        zb = group_bbox(zg)
        if not zb:
            continue
        zcx, zcy = zb[0] + zb[2] / 2, zb[1] + zb[3] / 2
        best_j, best_d = None, 1e18
        for j, xg in enumerate(xing_groups):
            if j in used_x:
                continue
            xb = group_bbox(xg)
            if not xb:
                continue
            xcx, xcy = xb[0] + xb[2] / 2, xb[1] + xb[3] / 2
            d = np.hypot(zcx - xcx, zcy - xcy)
            size = max(zb[2], zb[3], xb[2], xb[3])
            if d < size * 1.15 and d < best_d:
                best_d, best_j = d, j
        if best_j is not None:
            used_x.add(best_j)
            pairs.append((zg, xing_groups[best_j]))
        else:
            pairs.append((zg, []))

    for j, xg in enumerate(xing_groups):
        if j not in used_x:
            pairs.append(([], xg))
    return pairs


def recognize(image_path: Path) -> List[DetectedStamp]:
    """底层印章检测（不含表格切分）。完整流程请用 pipeline.py。"""
    from digit_ocr import recognize_corners

    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(image_path)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    blue = mask_blue(hsv)
    yellow = mask_yellow(hsv)

    def expand_by_area(comps: List[Dict]) -> List[Dict]:
        if not comps:
            return []
        areas = sorted(c["area"] for c in comps)
        median = float(np.percentile(areas, 35))
        out: List[Dict] = []
        for c in comps:
            out.extend(split_overlapping_blob(c, median))
        return out

    zhi_exp = expand_by_area(find_components(blue, min_area=600))
    xing_exp = expand_by_area(find_components(yellow, min_area=500))
    pairs = merge_groups_for_pair(cluster_nearby(zhi_exp), cluster_nearby(xing_exp))

    results: List[DetectedStamp] = []
    for zg, xg in pairs:
        mid, name, conf = classify_group(zg, xg, bgr=img)
        if mid == 0:
            continue
        bb = group_bbox(zg) or group_bbox(xg)
        digits = CornerDigits()
        if zg and bb:
            mapped = recognize_corners(img, corner_rois(bb), bbox=bb)
            digits = CornerDigits(
                tl=mapped.get("左上"),
                tr=mapped.get("右上"),
                bl=mapped.get("左下"),
                br=mapped.get("右下"),
            )
        results.append(
            DetectedStamp(
                method_id=mid,
                method_name=name,
                confidence=conf,
                seal_count_zhi=len(zg),
                seal_count_xing=len(xg),
                corner_digits=digits,
                bbox=bb,
            )
        )
    return results


def draw_debug(image_path: Path, results: List[DetectedStamp], out_path: Path) -> None:
    img = cv2.imread(str(image_path))
    for r in results:
        if not r.bbox:
            continue
        x, y, w, h = r.bbox
        color = (30, 80, 200) if r.seal_count_zhi else (0, 180, 220)
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        label = f"{r.method_id}:{r.method_name}"
        cv2.putText(
            img, label, (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA,
        )
        if r.seal_count_zhi:
            for name, roi in corner_rois(r.bbox).items():
                rx, ry, rw, rh = roi
                cv2.rectangle(img, (rx, ry), (rx + rw, ry + rh), (20, 60, 180), 1)
    cv2.imwrite(str(out_path), img)


def main() -> None:
    parser = argparse.ArgumentParser(description="印章叠盖识别原型")
    parser.add_argument("image", type=Path, help="输入图片")
    parser.add_argument("--show", action="store_true", help="写出调试图")
    parser.add_argument(
        "--out", type=Path, default=ROOT / "output" / "debug.jpg",
        help="调试图路径",
    )
    args = parser.parse_args()

    results = recognize(args.image)
    payload = []
    for r in results:
        payload.append(
            {
                "method_id": r.method_id,
                "method_name": r.method_name,
                "confidence": round(r.confidence, 3),
                "zhi": r.seal_count_zhi,
                "xing": r.seal_count_xing,
                "corner_digits": r.corner_digits.as_dict(),
                "bbox": r.bbox,
            }
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n共检测到 {len(payload)} 组印章")
    print("提示：完整「裁格+OCR」请运行 python src/pipeline.py <图片> --show")

    if args.show:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        draw_debug(args.image, results, args.out)
        print(f"调试图已写入: {args.out}")


if __name__ == "__main__":
    main()
