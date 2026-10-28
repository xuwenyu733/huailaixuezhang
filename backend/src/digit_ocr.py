"""
方章四角手写数字识别。

关键：章角自带印刷斜线，直接抠墨会把斜线当数字。
做法：把检测框对齐知章模板 → 差分得到「多出来的笔迹」→ 再识别。
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "assets" / "zhi_seal.png"

_DDDDOCR = None
_DDDDOCR_TRIED = False


def _get_ddddocr():
    global _DDDDOCR, _DDDDOCR_TRIED
    if _DDDDOCR_TRIED:
        return _DDDDOCR
    _DDDDOCR = None
    _DDDDOCR_TRIED = True
    try:
        import ddddocr

        _DDDDOCR = ddddocr.DdddOcr(show_ad=False)
    except Exception:
        _DDDDOCR = None
    return _DDDDOCR


@lru_cache(maxsize=1)
def _template_ink() -> Optional[np.ndarray]:
    img = cv2.imread(str(TEMPLATE_PATH))
    if img is None:
        return None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([90, 40, 40]), np.array([140, 255, 255]))
    # 稍膨胀，盖住印刷斜线/边框位置
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
    return mask


def _seal_ink(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    deep = cv2.inRange(hsv, np.array([90, 35, 25]), np.array([140, 255, 230]))
    thr = float(np.percentile(gray, 42))
    dark = (gray < thr).astype(np.uint8) * 255
    ink = cv2.bitwise_or(deep, dark)
    if (ink > 0).mean() > 0.5:
        ink = deep
    return ink


def _extra_ink_in_seal(bgr: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    """
    整枚知章：实际墨迹 - 模板墨迹 ≈ 手写数字。
    返回与 bbox 同尺寸的 extra mask；失败返回 None。
    """
    x, y, w, h = bbox
    H, W = bgr.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 - x0 < 20 or y1 - y0 < 20:
        return None
    crop = bgr[y0:y1, x0:x1]
    ink = _seal_ink(crop)
    tmpl = _template_ink()
    if tmpl is None:
        return ink
    tw = cv2.resize(tmpl, (ink.shape[1], ink.shape[0]), interpolation=cv2.INTER_NEAREST)
    # 也对 180° 模板取更贴合的那个
    tw180 = cv2.rotate(tw, cv2.ROTATE_180)
    def score(t):
        inter = cv2.bitwise_and(ink, t)
        return float(inter.sum()) / max(float(t.sum()), 1)
    t_use = tw if score(tw) >= score(tw180) else tw180
    # 多出来的墨：在 ink 里、不在（膨胀后的）模板里
    extra = cv2.bitwise_and(ink, cv2.bitwise_not(t_use))
    # 去碎点
    extra = cv2.morphologyEx(
        extra, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    )
    return extra


def _corner_slice(
    mask: np.ndarray, corner: str, frac: float = 0.42
) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    h, w = mask.shape[:2]
    s = max(8, int(min(w, h) * frac))
    if corner == "左上":
        return mask[0:s, 0:s], (0, 0, s, s)
    if corner == "右上":
        return mask[0:s, w - s : w], (w - s, 0, s, s)
    if corner == "左下":
        return mask[h - s : h, 0:s], (0, h - s, s, s)
    return mask[h - s : h, w - s : w], (w - s, h - s, s, s)


def _to_patch(digit_mask: np.ndarray) -> Optional[np.ndarray]:
    ys, xs = np.where(digit_mask > 0)
    if len(xs) < 12:
        return None
    y0, y1 = max(0, ys.min() - 2), min(digit_mask.shape[0], ys.max() + 3)
    x0, x1 = max(0, xs.min() - 2), min(digit_mask.shape[1], xs.max() + 3)
    crop = digit_mask[y0:y1, x0:x1]
    # 放大
    scale = max(3.0, 56 / max(crop.shape))
    big = cv2.resize(
        crop,
        (max(8, int(crop.shape[1] * scale)), max(8, int(crop.shape[0] * scale))),
        interpolation=cv2.INTER_CUBIC,
    )
    pad = 10
    canvas = np.zeros((big.shape[0] + pad * 2, big.shape[1] + pad * 2), np.uint8)
    canvas[pad : pad + big.shape[0], pad : pad + big.shape[1]] = big
    # 放进 64x64 白底黑字
    bh, bw = canvas.shape
    sc = 48 / max(bh, bw)
    nh, nw = max(1, int(bh * sc)), max(1, int(bw * sc))
    resized = cv2.resize(canvas, (nw, nh), interpolation=cv2.INTER_AREA)
    out = np.full((64, 64), 255, np.uint8)
    yo, xo = (64 - nh) // 2, (64 - nw) // 2
    out[yo : yo + nh, xo : xo + nw] = np.where(resized > 0, 0, 255)
    return out


def extract_digits_from_seal(
    bgr: np.ndarray, bbox: Tuple[int, int, int, int]
) -> Dict[str, Optional[np.ndarray]]:
    """对一枚/一组知章框，提取四角数字 patch。"""
    extra = _extra_ink_in_seal(bgr, bbox)
    out: Dict[str, Optional[np.ndarray]] = {
        "左上": None, "右上": None, "左下": None, "右下": None
    }
    if extra is None:
        return out

    # 放大 extra 便于连通域
    eh, ew = extra.shape[:2]
    scale = max(2.0, 160 / max(eh, ew))
    big = cv2.resize(
        extra,
        (max(1, int(ew * scale)), max(1, int(eh * scale))),
        interpolation=cv2.INTER_NEAREST,
    )
    big = cv2.dilate(big, np.ones((2, 2), np.uint8), iterations=1)

    for corner in out:
        region, _ = _corner_slice(big, corner, frac=0.44)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(region, 8)
        if n <= 1:
            continue
        best_i, best_a = None, 0
        rh, rw = region.shape[:2]
        for i in range(1, n):
            area = int(stats[i, cv2.CC_STAT_AREA])
            bw = int(stats[i, cv2.CC_STAT_WIDTH])
            bh = int(stats[i, cv2.CC_STAT_HEIGHT])
            if area < 28 or area > rh * rw * 0.5:
                continue
            if bh < 8 and bw < 8:
                continue
            aspect = bh / max(bw, 1)
            if aspect < 0.35 or aspect > 6.0:
                continue
            # 贴边极细短线多半是斜线残留
            if area < 55 and max(bw, bh) < 14:
                continue
            if area > best_a:
                best_a, best_i = area, i
        if best_i is None or best_a < 40:
            continue
        digit = (labels == best_i).astype(np.uint8) * 255
        out[corner] = _to_patch(digit)
    return out


@lru_cache(maxsize=1)
def _digit_templates() -> List[Tuple[int, np.ndarray]]:
    templates: List[Tuple[int, np.ndarray]] = []
    for d in range(10):
        for scale in (0.7, 0.95, 1.15, 1.35):
            for thick in (1, 2, 3):
                cv = np.full((64, 64), 255, np.uint8)
                cv2.putText(
                    cv, str(d), (10, 50), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, 0, thick, cv2.LINE_AA,
                )
                templates.append((d, cv))
        if Image is not None:
            img = Image.new("L", (64, 64), 255)
            ImageDraw.Draw(img).text((14, 6), str(d), fill=0)
            templates.append((d, np.array(img)))
    return templates


def _match_template(patch: np.ndarray) -> Tuple[Optional[int], float]:
    temps = _digit_templates()
    if not temps:
        return None, 0.0
    best_d, best_s = None, -1.0
    a0 = patch.astype(np.float32)
    a0 = (a0 - a0.mean()) / (a0.std() + 1e-6)
    for d, t in temps:
        b = t.astype(np.float32)
        b = (b - b.mean()) / (b.std() + 1e-6)
        score = float((a0 * b).mean())
        if score > best_s:
            best_s, best_d = score, d
    if best_s < 0.20:
        return None, best_s
    return best_d, best_s


def _row_peaks(crop: np.ndarray) -> int:
    """左侧水平凹凸次数：3 常见 2~3 段，1/0 更少。"""
    if crop.size == 0:
        return 0
    hh, ww = crop.shape
    left = crop[:, : max(1, ww // 2)]
    row = left.sum(axis=1).astype(np.float32)
    if row.max() < 1:
        return 0
    # 平滑
    if len(row) >= 5:
        k = np.array([1, 2, 3, 2, 1], np.float32)
        row = np.convolve(row, k / k.sum(), mode="same")
    thr = max(row.max() * 0.40, 1.0)
    segs = 0
    in_seg = False
    for v in row:
        if v >= thr and not in_seg:
            segs += 1
            in_seg = True
        elif v < thr * 0.75:
            in_seg = False
    return segs


def _geom(patch: np.ndarray) -> Tuple[Optional[int], float]:
    ink = (patch < 128).astype(np.uint8)
    if ink.sum() < 12:
        return None, 0.0
    ys, xs = np.where(ink > 0)
    h = ys.max() - ys.min() + 1
    w = xs.max() - xs.min() + 1
    aspect = h / max(w, 1)
    fill = float(ink.sum()) / max(h * w, 1)
    cnts, hier = cv2.findContours(ink, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    holes = 0
    if hier is not None:
        holes = sum(1 for i in range(len(hier[0])) if hier[0][i][3] >= 0)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop = ink[y0:y1, x0:x1]
    hh, ww = crop.shape
    bands = [float(crop[i * hh // 3 : (i + 1) * hh // 3].mean()) for i in range(3)]
    left = float(crop[:, : max(1, ww // 2)].mean())
    right = float(crop[:, ww // 2 :].mean())
    peaks = _row_peaks(crop)

    scores = {d: 0.0 for d in range(10)}

    # 1：瘦、填充低、投影峰少（斜笔 1 也适用）
    if aspect >= 1.6 and holes == 0 and fill <= 0.48 and peaks <= 2:
        scores[1] += 0.7
    if aspect >= 1.9 and fill <= 0.42:
        scores[1] += 0.25
    if peaks <= 1 and aspect >= 1.5 and holes == 0:
        scores[1] += 0.2

    # 3：右侧更密（竖脊在右）；低清「3」常被误判有孔
    if right > left * 1.05 and 1.15 <= aspect <= 2.5 and fill >= 0.32:
        scores[3] += 0.55
    if peaks >= 2 and right >= left:
        scores[3] += 0.45
    if bands[0] > 0.1 and bands[2] > 0.1 and right > left:
        scores[3] += 0.3
    if holes >= 1 and right > left and fill >= 0.35:
        scores[3] += 0.4
        scores[0] -= 0.35
    # 右密 + 中等偏高填充：即使 peaks=1 也倾向 3（实心块状 3）
    if right > left * 1.15 and 0.45 <= fill <= 0.78 and aspect <= 2.2 and peaks <= 2:
        scores[3] += 0.35

    # 2：上下都有墨；左右较均衡（区别于右脊明显的 3）
    bal = abs(right - left) / max(right, left, 1e-6)
    if 1.0 <= aspect <= 2.2 and peaks <= 3 and fill >= 0.25:
        if bands[0] > 0.1 and bands[2] > 0.12:
            scores[2] += 0.45
        if bands[2] >= bands[0] * 0.8 and bal <= 0.25:
            scores[2] += 0.45
            scores[3] -= 0.25
        if left >= right * 0.9 and bands[2] > 0.15:
            scores[2] += 0.25

    # 0：真正闭环；若多峰则降权
    if holes >= 1 and 0.85 <= aspect <= 1.7 and peaks <= 2:
        scores[0] += 0.4
    if holes >= 1 and peaks <= 1:
        scores[0] += 0.2
    if holes >= 1:
        scores[4] += 0.15
    if bands[0] > bands[2] * 1.35 and holes == 0 and peaks <= 2:
        scores[7] += 0.35
    if holes == 0 and bands[0] > bands[1] and peaks >= 2:
        scores[5] += 0.2

    # 残渣：墨太少 / 太碎
    if ink.sum() < 35:
        return None, 0.0
    if fill < 0.22 and peaks <= 1 and aspect > 1.2:
        return None, 0.0
    # 实心三角块：多半是章角印刷残留，不是手写数字
    if fill >= 0.62 and aspect <= 1.45 and peaks <= 2:
        return None, 0.0

    best = max(scores, key=scores.get)
    if scores[best] < 0.5:
        return None, scores[best]
    return best, scores[best]


def _dddd(patch: np.ndarray) -> Tuple[Optional[int], float]:
    ocr = _get_ddddocr()
    if ocr is None:
        return None, 0.0
    big = cv2.resize(patch, (128, 128), interpolation=cv2.INTER_CUBIC)
    ink = (big < 128).astype(np.uint8) * 255
    ink = cv2.dilate(ink, np.ones((2, 2), np.uint8), iterations=1)
    big = np.where(ink > 0, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".png", big)
    if not ok:
        return None, 0.0
    try:
        text = ocr.classification(buf.tobytes())
    except Exception:
        return None, 0.0
    text = (text or "").strip()
    if re.fullmatch(r"[0-9]", text):
        return int(text), 0.9
    mapping = {"l": 1, "I": 1, "i": 1, "|": 1, "z": 2, "Z": 2, "s": 5, "S": 5}
    if text in mapping:
        return mapping[text], 0.55
    m = re.search(r"[0-9]", text)
    if m and len(re.sub(r"\s", "", text)) <= 2:
        return int(m.group()), 0.65
    return None, 0.0


def recognize_digit_patch(patch: np.ndarray) -> Optional[int]:
    dg, sg = _geom(patch)
    dt, st = _match_template(patch)
    do, so = _dddd(patch)
    # 几何为主；模板/dddd 仅作佐证，避免残渣被模板硬认成数字
    if dg is not None and sg >= 0.55:
        return dg
    if dg is not None and sg >= 0.45 and (dt == dg or do == dg):
        return dg
    if dg is not None and dt is not None and dg == dt and sg + st >= 0.7:
        return dg
    # 几何很不确定时宁缺勿滥
    return None


def recognize_corners(
    bgr: np.ndarray,
    rois: Dict[str, Tuple[int, int, int, int]],
    bbox: Optional[Tuple[int, int, int, int]] = None,
    candidates: Optional[List[Dict]] = None,
) -> Dict[str, Optional[int]]:
    """
    优先用整章模板差分；若无 bbox 则退回逐角 ROI（兼容旧调用）。
    """
    del candidates
    result: Dict[str, Optional[int]] = {
        "左上": None, "右上": None, "左下": None, "右下": None
    }

    if bbox is not None:
        patches = extract_digits_from_seal(bgr, bbox)
        for k, p in patches.items():
            if p is None:
                continue
            result[k] = recognize_digit_patch(p)
        return result

    # 无 bbox：把四角 ROI 拼不起来，只能逐角弱识别
    for name, roi in rois.items():
        x, y, w, h = roi
        crop = bgr[y : y + h, x : x + w]
        if crop.size == 0:
            continue
        ink = _seal_ink(crop)
        ink = cv2.resize(ink, (80, 80), interpolation=cv2.INTER_NEAREST)
        # 去边
        e = 6
        ink[:e, :] = 0
        ink[-e:, :] = 0
        ink[:, :e] = 0
        ink[:, -e:] = 0
        patch = _to_patch(ink)
        if patch is not None:
            result[name] = recognize_digit_patch(patch)
    return result


def recognize_digit(
    bgr: np.ndarray, roi: Tuple[int, int, int, int]
) -> Optional[int]:
    return recognize_corners(bgr, {"左上": roi}).get("左上")


def find_digit_candidates(bgr: np.ndarray, **kwargs) -> List[Dict]:
    return []


def assign_digits_to_corners(*args, **kwargs):
    return {"左上": None, "右上": None, "左下": None, "右下": None}
