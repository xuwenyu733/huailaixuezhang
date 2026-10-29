"""四角数字的二次核对：固定角窗放大读数。

为什么不用墨迹定位（src/digit_locate.py）：
墨迹连通域有时定位到章框线段而不是数字，且漏检率高（全页只能覆盖约 2/3 的角）。
固定角窗不依赖定位 —— 直接以整组 bbox 的角点为中心取一个方窗、向外偏 6%，
再放大到 384px。数字落在 bbox 外 10~20% 也能被窗户罩住。

实测（assets/sample_page_hi.jpg，69 个有数字的角）：
- 单窗读：0.45 倍窗 51/69、0.65 倍窗 58/69，都不如整组读（63/69），不能整体替换；
- 三窗多数（0.45 / 0.65 / 内移 0.55）：左下角 8/10，能救回整组读错、被裁切切掉笔画的角；
- 角上的数字常压在 bbox 边缘外一点，固定窗会切掉半笔（#15 左下、#21 右上 都是这样读错的），
  所以第二个尺度仍不一致时要补一个「向格内移 14%」的窗做裁决；
- 数字的书写方向每个角都不一样（#8 要转 +40° 才像 5，#25 要转 −40° 才像 2），
  试过旋转拼图与固定角度投票都没有收益，所以不做方向纠正，只在 2↔3 这对混淆上自动改。
"""

from __future__ import annotations

from collections import Counter
from typing import Optional, Tuple

import cv2
import numpy as np

from corner_ocr import read_digit
from deepseek_ocr import fatal_reason

CORNERS = ("左上", "右上", "左下", "右下")


def window(img: np.ndarray, bbox, corner: str, side_ratio: float = 0.45,
           out: int = 384, outward: float = 0.06) -> Optional[np.ndarray]:
    """以 bbox 角点为中心的固定方窗，向外偏 outward*side，放大到 out×out。"""
    x, y, w, h = [float(v) for v in bbox]
    left = corner in ("左上", "左下")
    top = corner in ("左上", "右上")
    side = min(w, h) * side_ratio
    cx = (x if left else x + w) + (-1 if left else 1) * side * outward
    cy = (y if top else y + h) + (-1 if top else 1) * side * outward
    return _cut(img, cx, cy, side, out)


def inner(img: np.ndarray, bbox, corner: str, side_ratio: float = 0.55,
          inset: float = 0.14, out: int = 384) -> Optional[np.ndarray]:
    """把窗口往格子内部挪 inset*side。

    角上的数字常常压在 bbox 边缘外侧一点，固定窗会把笔画切掉一半（实测 #15 左下、
    #21 右上 都是这样被读错的）。内移窗的取景不同，两路一起看能恢复。
    """
    x, y, w, h = [float(v) for v in bbox]
    left = corner in ("左上", "左下")
    top = corner in ("左上", "右上")
    side = min(w, h) * side_ratio
    cx = (x if left else x + w) + (1 if left else -1) * side * inset
    cy = (y if top else y + h) + (1 if top else -1) * side * inset
    return _cut(img, cx, cy, side, out)


def _cut(img, cx, cy, side, out) -> Optional[np.ndarray]:
    H, W = img.shape[:2]
    x0, y0 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
    x1, y1 = int(min(W, cx + side / 2)), int(min(H, cy + side / 2))
    c = img[y0:y1, x0:x1]
    if c.size == 0 or c.shape[0] < 8 or c.shape[1] < 8:
        return None
    return cv2.resize(c, (out, out), interpolation=cv2.INTER_CUBIC)


def has_ink(crop: Optional[np.ndarray], v_max: int = 115, dg_max: int = 45,
            min_ratio: float = 0.004) -> bool:
    """窗里是否真有手写墨迹。

    只按亮度判定不行：章框和虚线纹也够暗，模型会把框线读成「1」（实测记录页 #26
    四个角都没写字，却被补了一个 1）。手写墨迹是近黑的，印章是纯蓝，通道差能分开：
    - 手写墨迹 B−G ≈ 23~31（近黑，三通道一起低）
    - 印章蓝/框线 B−G ≈ 61~97（B 高、G 极低）
    再对掩膜做一次 3x3 腐蚀，滤掉零星噪点。
    """
    if crop is None or not getattr(crop, "size", 0):
        return False
    B = crop[:, :, 0].astype(np.int16)
    G = crop[:, :, 1].astype(np.int16)
    V = crop.max(2)
    m = ((V < v_max) & ((B - G) < dg_max)).astype(np.uint8)
    if not m.any():
        return False
    return float(cv2.erode(m, np.ones((3, 3), np.uint8)).mean()) >= min_ratio


def read_corner(img: np.ndarray, bbox, corner: str, side_ratio: float = 0.45,
                client=None) -> Tuple[Optional[int], Optional[np.ndarray]]:
    """读一个角，返回 (数字或 None, 放大图)。"""
    crop = window(img, bbox, corner, side_ratio)
    if not has_ink(crop):
        return None, crop
    try:
        return read_digit(crop, client=client), crop
    except Exception:  # noqa: BLE001
        return None, crop


def read_corner3(img: np.ndarray, bbox, corner: str, client=None, errors: list | None = None,
                 stop: dict | None = None):
    """三窗多数读角：0.45 外偏、0.65 外偏、0.55 内移，取≥2 一致者。

    两窗先读；一致就直接用（省一次调用），不一致再读内移窗做裁决。
    返回 (数字或 None, 用于展示的放大图, 三个读数)。
    `errors` 传入列表时，单窗读失败的原因会追加进去 —— 否则一次接口抖动
    只会表现为「这个角没读到」，看不出是「本来没字」还是「调用失败」。
    `stop` 传入共享 dict 时，一旦出现「无余额/密钥失效」这类致命错误就置
    `stop["fatal"]`，后续窗和后续组不再发请求（一次 402 不该变成几十次重试）。
    """
    a_crop = window(img, bbox, corner, 0.45)
    if not has_ink(a_crop):
        return None, a_crop, []

    def guard(e) -> None:
        if errors is not None:
            errors.append(f"{corner}读窗失败 {type(e).__name__}: {e}")
        if stop is not None and not stop.get("fatal"):
            stop["fatal"] = fatal_reason(e)

    try:
        a = read_digit(a_crop, client=client)
    except Exception as e:  # noqa: BLE001
        a = None
        guard(e)
    if stop and stop.get("fatal"):
        return None, a_crop, []
    b_crop = window(img, bbox, corner, 0.65)
    try:
        b = read_digit(b_crop, client=client) if has_ink(b_crop) else None
    except Exception as e:  # noqa: BLE001
        b = None
        guard(e)
    if a is not None and a == b:
        return a, a_crop, [a, b]
    if stop and stop.get("fatal"):
        return None, a_crop, [a, b]

    c_crop = inner(img, bbox, corner, 0.55)
    try:
        c = read_digit(c_crop, client=client) if has_ink(c_crop) else None
    except Exception as e:  # noqa: BLE001
        c = None
        guard(e)
    votes = [x for x in (a, b, c) if x is not None]
    if not votes:
        return None, a_crop, [a, b, c]
    counts = Counter(votes)
    val, n = counts.most_common(1)[0]
    return (val if n >= 2 else None), a_crop, [a, b, c]
