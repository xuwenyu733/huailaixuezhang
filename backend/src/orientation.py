"""
知章朝向：正向(0°) vs 引导(180°)。
用知章模板做归一化互相关，并辅以墨迹重心上下分布。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "assets" / "zhi_seal.png"


@lru_cache(maxsize=1)
def _zhi_templates() -> List[Tuple[int, np.ndarray]]:
    img = cv2.imread(str(TEMPLATE_PATH))
    if img is None:
        return []
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([90, 40, 40]), np.array([140, 255, 255]))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ink = cv2.bitwise_or(cv2.bitwise_not(gray), mask)
    ink = cv2.resize(ink, (64, 64), interpolation=cv2.INTER_AREA)
    out = [(0, ink), (180, cv2.rotate(ink, cv2.ROTATE_180))]
    return out


def _crop_ink(bgr: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    x, y, w, h = bbox
    H, W = bgr.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 - x0 < 12 or y1 - y0 < 12:
        return None
    crop = bgr[y0:y1, x0:x1]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([95, 50, 40]), np.array([135, 255, 230]))
    if mask.mean() < 8:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mask = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 8
        )
    return cv2.resize(mask, (64, 64), interpolation=cv2.INTER_AREA)


def match_orientation(bgr: np.ndarray, bbox: Tuple[int, int, int, int]) -> Tuple[int, float]:
    """
    返回 (0 或 180, 置信差)。
    置信差越大，朝向越明确。
    """
    patch = _crop_ink(bgr, bbox)
    temps = _zhi_templates()
    if patch is None or not temps:
        return 0, 0.0

    scores: Dict[int, float] = {}
    a = patch.astype(np.float32)
    a = (a - a.mean()) / (a.std() + 1e-6)
    for deg, t in temps:
        b = t.astype(np.float32)
        b = (b - b.mean()) / (b.std() + 1e-6)
        scores[deg] = float((a * b).mean())

    # 墨迹上下分布：正向花在上，引导章花在下
    top = float(patch[:28, 16:48].mean())
    bot = float(patch[36:, 16:48].mean())
    polarity = (top - bot) / 255.0  # >0 更像正向

    s0, s180 = scores.get(0, -1.0), scores.get(180, -1.0)
    s0 += 0.08 * polarity
    s180 -= 0.08 * polarity
    if s180 > s0:
        return 180, float(s180 - s0)
    return 0, float(s0 - s180)


def orientations_in_group(
    bgr: np.ndarray, zhi_group: List[Dict]
) -> List[int]:
    """对组内每枚知章估计朝向。"""
    degs = []
    for c in zhi_group:
        bbox = (int(c["x"]), int(c["y"]), int(c["w"]), int(c["h"]))
        deg, _ = match_orientation(bgr, bbox)
        degs.append(deg)
    return degs


def classify_zhi_layout(
    zhi_group: List[Dict], degs: List[int]
) -> Tuple[int, str, float]:
    """结合数量、朝向、相对位置细分类纯知章盖法。"""
    n = len(zhi_group)
    n180 = sum(1 for d in degs if d == 180)
    n0 = n - n180

    if n == 1:
        if degs and degs[0] == 180:
            return 2, "引导章（知章）", 0.82
        return 1, "正向章（知章）", 0.82

    if n == 2:
        # 改进章：一正一引导，且引导偏左上
        mixed = n0 == 1 and n180 == 1
        xs = [c["cx"] for c in zhi_group]
        ys = [c["cy"] for c in zhi_group]
        dx = abs(xs[0] - xs[1])
        dy = abs(ys[0] - ys[1])
        size = max(c["w"] + c["h"] for c in zhi_group) / 2
        offset = (dx + dy) / max(size, 1)

        if mixed:
            # 引导章应更靠左上
            pairs = list(zip(zhi_group, degs))
            guide = next(c for c, d in pairs if d == 180)
            fwd = next(c for c, d in pairs if d == 0)
            if guide["cx"] <= fwd["cx"] + 8 and guide["cy"] <= fwd["cy"] + 8:
                return 3, "改进章（知章）", 0.80
            return 3, "改进章（知章）", 0.72

        # 两枚都正向或都引导 → 二叠
        conf = 0.74 if offset > 0.25 else 0.66
        return 4, "知章二叠章", conf

    return 5, "知章三叠章", 0.70
