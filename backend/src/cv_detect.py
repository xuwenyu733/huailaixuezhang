"""CV 前处理：颜色分割定位每个「盖印单元」，并给出分组裁剪。

思路：
1. 蓝方章 / 黄圆章 颜色分离（按亮度自适应阈值，兼容不同曝光）；
2. 连通域 + 同行合并，得到一个个盖印单元（一组叠盖算一个单元）；
3. 按单元 bbox 外扩裁切并放大，交给视觉模型只判这一组。

之所以要分单元裁剪：整页 4096 图上每枚章只有百来像素，直接整页送模型
会被缩放到短边 768，角上数字仅剩几个像素，必然读错。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np

MAX_SIDE = 2400  # 工作图长边上限，够看清又不至于拖慢

# 诊断用：记录每次合并决策（gap/重叠率），由调用方清空读取
MERGE_DEBUG: List[dict] = []


@dataclass
class SealGroup:
    """一个盖印单元（一组叠盖的章）。"""

    bbox: Tuple[int, int, int, int]  # x0, y0, x1, y1（工作图坐标）
    blue_px: int
    yellow_px: int
    row: int = 0
    est_blue: int = 0
    est_yellow: int = 0

    @property
    def w(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def h(self) -> int:
        return self.bbox[3] - self.bbox[1]


def _masks(work: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    B, G, R = [work[:, :, i].astype(np.int16) for i in range(3)]
    V = work.max(2).astype(np.int16)
    paper_v = float(np.percentile(V, 90)) or 255.0
    dark = V < max(60.0, paper_v * 0.82)

    blue = ((B - R > 40) & (B > 90) & dark).astype(np.uint8) * 255
    yellow = ((G.astype(np.int16) - B > 40) & (G > 110) & (R > 100)).astype(np.uint8) * 255

    k = np.ones((5, 5), np.uint8)
    close = np.ones((11, 11), np.uint8)
    blue = cv2.morphologyEx(blue, cv2.MORPH_OPEN, k)
    blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, close)  # 把花瓣/线条连成整枚章
    yellow = cv2.morphologyEx(yellow, cv2.MORPH_OPEN, k)
    yellow = cv2.morphologyEx(yellow, cv2.MORPH_CLOSE, close)
    return blue, yellow


def prepare(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """缩小到工作尺寸，返回 (work, scale)，scale = work 相对原图的比例。"""
    h, w = image.shape[:2]
    scale = min(1.0, MAX_SIDE / max(h, w))
    if scale < 1.0:
        work = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    else:
        work = image
    return work, scale


def _overlap_ratio(a, b) -> float:
    """两个框的实际重叠面积 / 较小框面积。只「贴边」不算叠盖。"""
    ox = min(a[2], b[2]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[1], b[1])
    if ox <= 0 or oy <= 0:
        return 0.0
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return (ox * oy) / small if small else 0.0


def _near(a, b, tol: int = 6) -> bool:
    return not (a[2] + tol < b[0] or b[2] + tol < a[0] or a[3] + tol < b[1] or b[3] + tol < a[1])


def _fragment(box, stamp: float) -> bool:
    """短边明显小于单枚尺寸：一枚章被印框/纸纹切开的残片，需要并回主块。"""
    return min(box[2] - box[0], box[3] - box[1]) <= stamp * 0.60


def detect_groups(image: np.ndarray):
    """返回 (groups, work, blue_mask, yellow_mask, scale)。"""
    work, scale = prepare(image)
    blue, yellow = _masks(work)
    MERGE_DEBUG.clear()

    # 蓝、黄分别取连通域：避免同色像素把相邻的方章与圆章连成一个巨块
    comps = []
    for mask in (blue, yellow):
        n, _lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        for i in range(1, n):
            x, y, cw, ch, area = stats[i]
            if area < 1200 or cw < 20 or ch < 20:
                continue
            if cw > work.shape[1] * 0.6 or ch > work.shape[0] * 0.6:  # 整页级的误检
                continue
            comps.append([int(x), int(y), int(x + cw), int(y + ch), int(area)])
    if not comps:
        return [], work, blue, yellow, scale

    stamp = float(np.median([c[3] - c[1] for c in comps]))

    # 去掉细长噪声（书脊、页脚、表格线）：印章近似正方，长宽比不会太夸张
    comps = [
        c
        for c in comps
        if min(c[2] - c[0], c[3] - c[1]) > stamp * 0.22
        and max(c[2] - c[0], c[3] - c[1]) < stamp * 3.6
        and max(c[2] - c[0], c[3] - c[1]) / max(1, min(c[2] - c[0], c[3] - c[1])) < 2.6
    ]
    if not comps:
        return [], work, blue, yellow, scale

    # 先按 y 中心分行
    comps.sort(key=lambda c: (c[1] + c[3]) / 2)
    rows: List[dict] = []
    for c in comps:
        cy = (c[1] + c[3]) / 2
        for r in rows:
            if abs(cy - r["cy"]) < stamp * 0.55:
                r["items"].append(c)
                r["cy"] = float(np.mean([(i[1] + i[3]) / 2 for i in r["items"]]))
                break
        else:
            rows.append({"cy": cy, "items": [c]})

    groups: List[SealGroup] = []
    for ri, r in enumerate(sorted(rows, key=lambda r: r["cy"])):
        items = sorted(r["items"], key=lambda c: c[0])
        cur = list(items[0])
        merged: List[List[int]] = []
        for c in items[1:]:
            gap = c[0] - cur[2]
            vov = min(cur[3], c[3]) - max(cur[1], c[1])
            w_new = max(cur[2], c[2]) - cur[0]
            # 只有「水平方向真重叠」或「并完仍不超过单枚宽度」才算同一组。
            # 并排的两枚独立章 gap 为正、合并后接近 2×stamp，必须保持分开：
            # 否则两枚相邻正向章会被读成二叠，相邻的行章会被算进知章里。
            same_unit = gap < 0 or w_new <= stamp * 1.45
            cand = vov > stamp * 0.25
            if cand:
                MERGE_DEBUG.append(
                    {
                        "kind": "same_row",
                        "row": ri,
                        "merged": bool(same_unit),
                        "gap": int(gap),
                        "gap_ratio": round(gap / stamp, 3),
                        "vov_ratio": round(vov / stamp, 3),
                        "stamp": round(stamp, 1),
                        "w_before": int(cur[2] - cur[0]),
                        "w_after": int(w_new),
                        "w_after_ratio": round(w_new / stamp, 2),
                        "box": [int(cur[0]), int(cur[1]), int(w_new), int(max(cur[3], c[3]) - cur[1])],
                    }
                )
            if cand and same_unit:
                cur[2] = max(cur[2], c[2])
                cur[3] = max(cur[3], c[3])
                cur[4] += c[4]
            else:
                merged.append(cur)
                cur = list(c)
        merged.append(cur)
        for m in merged:
            x0, y0, x1, y1 = m[:4]
            groups.append(
                SealGroup(
                    bbox=(x0, y0, x1, y1),
                    blue_px=int((blue[y0:y1, x0:x1] > 0).sum()),
                    yellow_px=int((yellow[y0:y1, x0:x1] > 0).sum()),
                    row=ri,
                )
            )

    # 叠盖修边：真重叠（ovr≥0.15）的多半是知行对章被拆成蓝、黄两块；
    # 残片（短边远小于单枚）贴到主块时也并回去，避免把印框切开的一枚章当成两枚。
    merged_any = True
    while merged_any:
        merged_any = False
        out: List[SealGroup] = []
        for g in groups:
            for o in out:
                ovr = _overlap_ratio(o.bbox, g.bbox) if o.row == g.row else 0.0
                frag = _fragment(o.bbox, stamp) or _fragment(g.bbox, stamp)
                # 真叠盖（同排、重叠明显）；或残片贴近主块（残片可能被印框切到邻排）
                merge_ok = (o.row == g.row and ovr >= 0.15) or (frag and _near(o.bbox, g.bbox))
                if merge_ok:
                    MERGE_DEBUG.append(
                        {
                            "kind": "cross",
                            "row": g.row,
                            "merged": True,
                            "ovr": round(ovr, 3),
                            "fragment": bool(frag),
                            "a": list(o.bbox),
                            "b": list(g.bbox),
                            "a_color": [o.blue_px, o.yellow_px],
                            "b_color": [g.blue_px, g.yellow_px],
                        }
                    )
                    o.bbox = (
                        min(o.bbox[0], g.bbox[0]),
                        min(o.bbox[1], g.bbox[1]),
                        max(o.bbox[2], g.bbox[2]),
                        max(o.bbox[3], g.bbox[3]),
                    )
                    merged_any = True
                    break
            else:
                out.append(g)
        groups = out
    for g in groups:
        x0, y0, x1, y1 = g.bbox
        g.blue_px = int((blue[y0:y1, x0:x1] > 0).sum())
        g.yellow_px = int((yellow[y0:y1, x0:x1] > 0).sum())

    # 用「纯色 + 单枚宽度」的组标定单枚油墨面积，据此估算每组枚数（作为给模型的参考）
    unit_b = [g.blue_px for g in groups if g.blue_px > 0 and g.yellow_px == 0 and g.w < stamp * 1.3]
    unit_y = [g.yellow_px for g in groups if g.yellow_px > 0 and g.blue_px == 0]
    b_unit = float(np.median(unit_b)) if unit_b else 0.0
    y_unit = float(np.median(unit_y)) if unit_y else 0.0
    for g in groups:
        if b_unit:
            g.est_blue = int(np.clip(round(g.blue_px / b_unit), 0, 3))
        if y_unit:
            g.est_yellow = int(np.clip(round(g.yellow_px / y_unit), 0, 3))

    return groups, work, blue, yellow, scale


def crop_group(work: np.ndarray, g: SealGroup, pad_ratio: float = 0.26, out_side: int = 640) -> np.ndarray:
    """按单元 bbox 外扩裁切，保证方章四角的手写数字不被切掉，再上采样。

    横向按「长边」外扩：知行对章是宽扁组（宽可达高的 1.8 倍），若只按高度取
    余量，右侧叠盖的黄章会被切掉一截，而第 9-11 种盖法正是靠黄章枚数区分。
    纵向仍按高度取，避免把上下相邻行的章带进来。
    """
    pad_y = int(max(12, g.h * pad_ratio))
    pad_x = int(max(12, max(g.w, g.h) * pad_ratio))
    H, W = work.shape[:2]
    x0 = max(0, g.bbox[0] - pad_x)
    y0 = max(0, g.bbox[1] - pad_y)
    x1 = min(W, g.bbox[2] + pad_x)
    y1 = min(H, g.bbox[3] + pad_y)
    crop = work[y0:y1, x0:x1].copy()
    if crop.size == 0:
        return crop
    s = out_side / min(crop.shape[:2])
    if s > 1:
        crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    return crop


def to_original(box: Tuple[int, int, int, int], scale: float) -> Tuple[int, int, int, int]:
    inv = 1.0 / scale if scale else 1.0
    return (
        int(box[0] * inv),
        int(box[1] * inv),
        int((box[2] - box[0]) * inv),
        int((box[3] - box[1]) * inv),
    )
