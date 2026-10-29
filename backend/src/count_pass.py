"""独立「只数枚数」通道 + 「改进章 vs 知章二叠」的模板相关判据。

为什么单独问一次枚数：
主识别调用要同时数枚数、读四角数字、判朝向，注意力被分散。实测（说明页 11 组）：
- 主调用把 p3 的「知行对章三叠」数成 2 蓝 + 2 黄（实际 3+3）；
- 单独问「几枚蓝章、几枚黄章」并说明「被压住的仍算一枚」，11/11 全对，且连跑两遍稳定；
- 唯一的系统性偏差是纯黄组的组会被补出幽灵蓝章（p2 #6 数成 1 蓝、#7 数成 2 蓝），
  用颜色像素量归零即可（实测蓝像素 0 vs 单枚 3200+，阈值 400 分得很开）。

改进章（3 号）与知章二叠（4 号）数量、位置完全一致，只差其中一枚是否旋转。
把本页「单枚蓝章」的那组当模板做相关匹配：
- 改进章：0° 与 180° 各有一个强峰，且两峰位置相差半枚以上（0.83 / 0.77）
- 知章二叠：只有一个方向有强峰（0.90 / 0.49）
这个差异在 p2 的 5 个蓝组上完全可分，只对「2 枚蓝章」的组启用。
"""

from __future__ import annotations

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Sequence

import cv2
import numpy as np

from cv_detect import crop_group

COUNT_SYSTEM = """只做计数，不要读任何数字或文字。这是一组叠盖的印章图案。
1. 蓝色方章（知章）有几枚？每枚 = 一朵蓝色五瓣花 + 一段蓝色手形（同一枚的花与手形各算一次，不要重复计数；
   被压住的那枚可能只露出部分花瓣或半个手形，仍算一枚）。
2. 黄色圆章（行章）有几枚？每枚 = 一个黄色圆环。
只输出 JSON：{"zhi_wu": n, "xing_wu": n}"""

COUNT_USER = "有几枚知章、几枚行章？"
COUNT_SIDE = 700  # 实测 700/860/1000 都全对，取最小以省时间

MIN_COLOR_PX = 400  # 低于此值认为该颜色不存在（单枚蓝章实测 3200+）
MIXED_SCORE = 0.55  # 峰值阈值
MIXED_RATIO = 0.55  # 两峰间距需超过 0.55 枚章宽


def _ask(client, crop: np.ndarray):
    ok, buf = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not ok:
        return None
    b64 = base64.b64encode(buf.tobytes()).decode()
    r = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {"role": "system", "content": COUNT_SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": COUNT_USER},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]},
        ],
        temperature=0,
        max_tokens=200,
        extra_body={"thinking": {"type": "disabled"}},
    )
    text = r.choices[0].message.content or ""
    try:
        d = json.loads(text[text.index("{"): text.rindex("}") + 1])
        z, x = d.get("zhi_wu"), d.get("xing_wu")
        if z is None or x is None:
            return None
        return int(z), int(x)
    except Exception:  # noqa: BLE001
        return None


def count_groups(work: np.ndarray, groups, client=None, workers: int = 6) -> List[Optional[tuple]]:
    """对每组单独问一次枚数，返回 [(zhi, xing) | None]。"""
    if client is None:
        from cell_ocr import _client

        client = _client()
    crops = [crop_group(work, g, out_side=COUNT_SIDE) for g in groups]

    def one(c):
        if c.size == 0:
            return None
        try:
            return _ask(client, c)
        except Exception:  # noqa: BLE001
            return None

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        return list(ex.map(one, crops))


def color_guard(counts: Sequence[Optional[tuple]], groups) -> List[Optional[tuple]]:
    """把「该颜色根本不存在」的枚数归零，压掉纯黄组被补出幽灵蓝章的问题。"""
    out = []
    for c, g in zip(counts, groups):
        if c is None:
            out.append(None)
            continue
        z, x = c
        if g.blue_px < MIN_COLOR_PX:
            z = 0
        if g.yellow_px < MIN_COLOR_PX:
            x = 0
        out.append((z, x))
    return out


def _soft(work: np.ndarray) -> np.ndarray:
    B, G, R = [work[:, :, i].astype(np.float32) for i in range(3)]
    return np.clip(B - (R + G) / 2, 0, 255)


def _peaks(res: np.ndarray, thr: float, min_dist: float):
    d = cv2.dilate(res, np.ones((9, 9), np.uint8))
    ys, xs = np.where((res >= thr) & (res >= d - 1e-6))
    out = sorted(((float(res[y, x]), int(x), int(y)) for y, x in zip(ys, xs)), reverse=True)
    keep = []
    for v, x, y in out:
        if all((x - kx) ** 2 + (y - ky) ** 2 > min_dist ** 2 for _, kx, ky in keep):
            keep.append((v, x, y))
    return keep


def _match(area: np.ndarray, tpl: np.ndarray, scales=(0.92, 0.96, 1.0, 1.04, 1.08)):
    best = None
    for s in scales:
        t = cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        if t.shape[0] >= area.shape[0] or t.shape[1] >= area.shape[1]:
            continue
        m = cv2.matchTemplate(area, t, cv2.TM_CCOEFF_NORMED)
        if best is None or m.max() > best.max():
            best = m
    return best


def mixed_flags(work: np.ndarray, groups, blue_mask: np.ndarray,
                counts: Sequence[Optional[tuple]]) -> List[int]:
    """返回「2 枚蓝章且一枚正向一枚旋转」的组下标（改进章）。"""
    soft = _soft(work)
    tpl_idx = None
    for i, (c, g) in enumerate(zip(counts, groups)):
        if c == (1, 0) and g.blue_px >= MIN_COLOR_PX:
            tpl_idx = i
            break
    if tpl_idx is None:
        return []
    g = groups[tpl_idx]
    x0, y0, x1, y1 = g.bbox
    n, _l, st, _c = cv2.connectedComponentsWithStats(blue_mask[y0:y1, x0:x1], 8)
    if n < 2:
        return []
    big = max(range(1, n), key=lambda k: st[k][4])
    bx, by, bw, bh = (int(v) for v in st[big][:4])
    tpl = soft[y0 + by:y0 + by + bh, x0 + bx: x0 + bx + bw]
    tpl = tpl[int(bh * 0.05): int(bh * 0.92), int(bw * 0.05): int(bw * 0.92)]
    if tpl.size == 0:
        return []
    min_dist = min(tpl.shape[:2]) * MIXED_RATIO

    out: List[int] = []
    for i, (c, gg) in enumerate(zip(counts, groups)):
        if c != (2, 0):  # 只判断「两枚蓝章」的组
            continue
        gx0, gy0, gx1, gy1 = gg.bbox
        dx, dy = int((gx1 - gx0) * 0.05), int((gy1 - gy0) * 0.05)
        H, W = soft.shape[:2]
        area = soft[max(0, gy0 - dy):min(H, gy1 + dy), max(0, gx0 - dx):min(W, gx1 + dx)]
        if area.shape[0] <= tpl.shape[0] + 4 or area.shape[1] <= tpl.shape[1] + 4:
            continue
        r0 = _match(area, tpl)
        r1 = _match(area, cv2.rotate(tpl, cv2.ROTATE_180))
        if r0 is None or r1 is None:
            continue
        p0 = _peaks(r0, MIXED_SCORE, min_dist)
        p1 = _peaks(r1, MIXED_SCORE, min_dist)
        if p0 and p1:
            d2 = (p0[0][1] - p1[0][1]) ** 2 + (p0[0][2] - p1[0][2]) ** 2
            if d2 > min_dist ** 2:
                out.append(i)
    return out
