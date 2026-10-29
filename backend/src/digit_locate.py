"""手写数字定位：把方章四角的手写数字从蓝色印章油墨里分出来，单独裁成小图。

为什么需要：整组图里左下角只有几十像素，模型会把 3 读成 2（人工校验确认 3/5 的错误都在这里）。
把数字本身抠出来放大到 200+ 像素后，同样的问题 12/12 全对。

做法：
1. 黑色墨迹 = 暗像素 且 不是蓝油墨、不是黄油墨；
2. 按连通域取候选（数字高度约占章宽的 1/8~1/4）；
3. 按「离四个角的距离」把候选分配到 左上/右上/左下/右下。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

CORNERS = ("左上", "右上", "左下", "右下")

# 各角相对 bbox 的搜索窗（比例），数字有时落在 bbox 外侧 10~20%
_WINDOWS = {
    "左上": (-0.28, -0.28, 0.48, 0.50),
    "右上": (0.52, -0.28, 1.28, 0.50),
    "左下": (-0.28, 0.50, 0.48, 1.28),
    "右下": (0.52, 0.50, 1.28, 1.28),
}
# 各角的「理想位置」（bbox 角点，按比例）
_ANCHOR = {"左上": (0.05, 0.05), "右上": (0.95, 0.05), "左下": (0.05, 0.95), "右下": (0.95, 0.95)}


@dataclass
class DigitBlob:
    box: Tuple[int, int, int, int]  # x0, y0, x1, y1
    area: int

    @property
    def cx(self) -> float:
        return (self.box[0] + self.box[2]) / 2

    @property
    def cy(self) -> float:
        return (self.box[1] + self.box[3]) / 2


def ink_mask(image: np.ndarray) -> np.ndarray:
    """手写数字的墨迹掩膜。

    注意：手写笔迹多数是蓝黑墨水，与蓝章油墨颜色接近，**按颜色分不开**
    （早期版本用 B-R 判蓝，候选只覆盖 64% 的角）。改为按亮度分：
    手写笔迹明显比印章油墨更暗，V<105 时全页候选约 119 个（实际数字 81 个），
    四角覆盖 22/24 组。
    """
    V = image.max(2).astype(np.int16)
    m = (V < 105).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return m


def find_blobs(mask: np.ndarray, min_area: int = 90, max_area: int = 4200) -> List[DigitBlob]:
    n, _lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    out: List[DigitBlob] = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if not (min_area <= a <= max_area):
            continue
        if not (6 <= w <= 90 and 6 <= h <= 90):
            continue
        if min(w, h) / max(w, h) < 0.18:  # 细长线：表格线、书脊
            continue
        if a / float(w * h) < 0.12:
            continue
        out.append(DigitBlob((int(x), int(y), int(x + w), int(y + h)), int(a)))
    return out


def assign_corners(bbox: Tuple[int, int, int, int], blobs: List[DigitBlob]) -> Dict[str, DigitBlob]:
    """把候选墨迹分配到四角；每角最多取一个（离理想角点最近的）。"""
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    picked: Dict[str, DigitBlob] = {}
    for name, (wx0, wy0, wx1, wy1) in _WINDOWS.items():
        ax, ay = _ANCHOR[name]
        target = (x0 + w * ax, y0 + h * ay)
        best: Optional[DigitBlob] = None
        best_d = min(w, h) * 0.55
        for b in blobs:
            if not (x0 + w * wx0 <= b.cx <= x0 + w * wx1 and y0 + h * wy0 <= b.cy <= y0 + h * wy1):
                continue
            d = ((b.cx - target[0]) ** 2 + (b.cy - target[1]) ** 2) ** 0.5
            if d < best_d:
                best, best_d = b, d
        if best is not None:
            picked[name] = best
    return picked


def crop_blob(image: np.ndarray, blob: DigitBlob, out_side: int = 224, pad_ratio: float = 0.28) -> np.ndarray:
    """按墨迹框紧裁 + 外扩，放大到 out_side，笔画居中。"""
    x0, y0, x1, y1 = blob.box
    side = max(x1 - x0, y1 - y0)
    pad = int(side * pad_ratio)
    cxs, cys = (x0 + x1) // 2, (y0 + y1) // 2
    half = side // 2 + pad
    H, W = image.shape[:2]
    ax0, ay0 = max(0, cxs - half), max(0, cys - half)
    ax1, ay1 = min(W, cxs + half), min(H, cys + half)
    crop = image[ay0:ay1, ax0:ax1]
    if crop.size == 0:
        return crop
    return cv2.resize(crop, (out_side, out_side), interpolation=cv2.INTER_CUBIC)


def grid4(tiles: Dict[str, np.ndarray], size: int = 224, gap: int = 8) -> np.ndarray:
    """四角拼成 2x2（左上/右上/左下/右下），缺的角放浅灰空块。"""
    blank = np.full((size, size, 3), 236, np.uint8)
    canvas = np.full((size * 2 + gap * 3, size * 2 + gap * 3, 3), 255, np.uint8)
    pos = {"左上": (0, 0), "右上": (0, 1), "左下": (1, 0), "右下": (1, 1)}
    for name, (r, c) in pos.items():
        t = tiles.get(name)
        if t is None:
            t = blank
        elif t.shape[0] != size or t.shape[1] != size:
            t = cv2.resize(t, (size, size))
        y = gap + r * (size + gap)
        x = gap + c * (size + gap)
        canvas[y : y + size, x : x + size] = t
    return canvas
