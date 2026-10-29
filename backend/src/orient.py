"""按「手形相对花心的方位」判断知章朝向（正向 / 旋转 180°）。

印章图案构成：蓝色方框 + 四角短斜线 + 中央五瓣花（花心是个小孔）+ 花心右下方一只手。
整枚旋转 180° 后，手形会跑到花心的左上方 —— 这是全图唯一有方向性的元素，
比让视觉模型「看手形」稳定得多（模型对 180° 基本不敏感）。

做法：蓝色连通域里最大的一块是花（花瓣彼此相连），手形是独立的一块，
面积约为花的 1/5 ~ 1/2。取「花质心 → 手质心」的向量：
  dy > 0（手在花下方）→ 正向
  dy < 0（手在花上方）→ 旋转 180°

只对「单枚知章」的组用（zhi==1 且 xing==0）。多枚叠盖时花瓣会连成一片、
手形位置不再对应单一一枚，判不准，交给模型。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class Blob:
    area: int
    cx: float
    cy: float
    w: int
    h: int


@dataclass
class Orient:
    rotated: Optional[bool]  # None = 判不出
    hands: int
    dy_ratio: float  # (手cy - 花cy) / 图长边，正=手在下方
    note: str = ""


def _blue_mask(img: np.ndarray) -> np.ndarray:
    B, G, R = [img[:, :, i].astype(np.int16) for i in range(3)]
    V = img.max(2).astype(np.int16)
    paper = float(np.percentile(V, 90)) or 255.0
    dark = V < max(60.0, paper * 0.82)
    m = ((B - R > 40) & (B > 90) & dark).astype(np.uint8) * 255
    # 只做极小开运算去掉抗锯齿毛刺；不能做闭运算，否则手形会和花粘成一块
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))


def _blobs(mask: np.ndarray, min_area: float) -> List[Blob]:
    n, _lab, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < min_area:
            continue
        out.append(Blob(int(a), float(cent[i][0]), float(cent[i][1]), int(w), int(h)))
    return out


def analyze(crop: np.ndarray) -> Orient:
    """在单组裁切图上判朝向。判不出时 rotated=None。"""
    if crop is None or not getattr(crop, "size", 0):
        return Orient(None, 0, 0.0, "空图")
    W = float(max(crop.shape[:2]))
    mask = _blue_mask(crop)
    blobs = _blobs(mask, min_area=W * W * 0.004)
    if len(blobs) < 2:
        return Orient(None, 0, 0.0, "蓝色连通域不足（可能整枚粘连）")

    blobs.sort(key=lambda b: -b.area)
    flower = blobs[0]
    hands = [
        b
        for b in blobs[1:]
        if 0.10 * flower.area <= b.area <= 0.60 * flower.area
        and np.hypot(b.cx - flower.cx, b.cy - flower.cy) < 0.55 * W
    ]
    if not hands:
        return Orient(None, 0, 0.0, "未找到手形连通域")
    # 手形取离花最近的那块（其余可能是别的章或方框残段）
    hands.sort(key=lambda b: np.hypot(b.cx - flower.cx, b.cy - flower.cy))
    hand = hands[0]
    dy = (hand.cy - flower.cy) / W
    dx = (hand.cx - flower.cx) / W
    if abs(dy) < 0.10:
        return Orient(None, len(hands), float(dy), f"手形与花心几乎同高(dy={dy:.2f},dx={dx:.2f})，判不出")
    return Orient(bool(dy < 0), len(hands), float(dy), f"花({flower.cx:.0f},{flower.cy:.0f}) 手({hand.cx:.0f},{hand.cy:.0f})")
