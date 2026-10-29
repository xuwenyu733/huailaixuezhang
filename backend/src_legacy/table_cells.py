"""
盖章处区域与印章单元切分。

表格线在扫描件上常被章盖住，因此不用强依赖线检测：
1. 估计「盖章处」列范围（排除左侧时间列）
2. 在印章检测结果上按 Y 聚类成行、按 X 分成单元
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np


@dataclass
class StampCell:
    """一个盖印单元（可能含叠盖多枚章）。"""

    row: int
    col: int
    bbox: Tuple[int, int, int, int]  # x,y,w,h（相对整页）
    pad_bbox: Tuple[int, int, int, int]  # 外扩后，含四角数字


def estimate_stamp_column(img: np.ndarray) -> Tuple[int, int]:
    """
    估计盖章处列的 [x0, x1)。
    优先找靠近左侧的竖线；否则用墨迹分布启发式。
    """
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bw = (gray < 175).astype(np.uint8) * 255
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(H // 15, 25)))
    vlines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk)
    col = (vlines > 0).sum(axis=0).astype(np.float32)

    # 在左 5%~35% 找最强竖线，作为时间|盖章处分界
    left, right = int(W * 0.05), int(W * 0.35)
    segment = col[left:right]
    if segment.max() > H * 0.12:
        x0 = left + int(np.argmax(segment)) + 2
    else:
        x0 = int(W * 0.12)

    # 右边去掉页边空白
    x1 = W - max(8, int(W * 0.02))
    return x0, x1


def estimate_table_top(img: np.ndarray, stamp_x0: int) -> int:
    """跳过标题区，估计盖章表内容起始 y。"""
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 表头横线：在上部找较长水平线
    bw = (gray < 175).astype(np.uint8) * 255
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(W // 10, 40), 1))
    hlines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk)
    row = (hlines > 0).sum(axis=1)
    thr = (W - stamp_x0) * 0.35
    candidates = [i for i in range(int(H * 0.02), int(H * 0.25)) if row[i] > thr]
    if not candidates:
        return int(H * 0.08)
    # 取第一簇横线下方
    y = candidates[0]
    for i in candidates:
        if i - y <= 4:
            y = i
        else:
            break
    return min(H - 1, y + 3)


def cluster_1d(
    values: Sequence[float], gap: float
) -> List[List[int]]:
    """对一维坐标聚类，返回每簇的原始下标列表。"""
    if not values:
        return []
    order = sorted(range(len(values)), key=lambda i: values[i])
    clusters: List[List[int]] = [[order[0]]]
    for idx in order[1:]:
        prev = values[clusters[-1][-1]]
        if values[idx] - prev <= gap:
            clusters[-1].append(idx)
        else:
            clusters.append([idx])
    return clusters


def cells_from_groups(
    groups: Sequence[Dict],
    img_shape: Tuple[int, int],
    stamp_x0: int,
    stamp_x1: int,
    pad: int = 22,
    row_gap: Optional[float] = None,
) -> List[StampCell]:
    """
    将印章组（含 bbox: x,y,w,h）编排为「行 × 列」盖印单元。
    groups 每项至少含 x,y,w,h,cx,cy。
    """
    H, W = img_shape[:2]
    # 过滤不在盖章列内的组
    usable = []
    for g in groups:
        cx = g.get("cx", g["x"] + g["w"] / 2)
        if stamp_x0 - 10 <= cx <= stamp_x1 + 10:
            usable.append(g)
    if not usable:
        return []

    heights = [g["h"] for g in usable]
    med_h = float(np.median(heights)) if heights else 60.0
    if row_gap is None:
        row_gap = med_h * 0.75

    cys = [g.get("cy", g["y"] + g["h"] / 2) for g in usable]
    row_clusters = cluster_1d(cys, row_gap)

    cells: List[StampCell] = []
    for r_i, idxs in enumerate(row_clusters):
        row_groups = [usable[i] for i in idxs]
        cxs = [g.get("cx", g["x"] + g["w"] / 2) for g in row_groups]
        # 同行内按中心距离再分列（并列多组）
        col_gap = float(np.median([g["w"] for g in row_groups])) * 0.95
        col_clusters = cluster_1d(cxs, col_gap)
        col_clusters = sorted(
            col_clusters,
            key=lambda ids: float(np.mean([row_groups[k].get("cx", 0) for k in ids])),
        )
        for c_i, c_ids in enumerate(col_clusters):
            gs = [row_groups[k] for k in c_ids]
            x0 = min(g["x"] for g in gs)
            y0 = min(g["y"] for g in gs)
            x1 = max(g["x"] + g["w"] for g in gs)
            y1 = max(g["y"] + g["h"] for g in gs)
            bbox = (x0, y0, x1 - x0, y1 - y0)
            px0 = max(stamp_x0, x0 - pad)
            py0 = max(0, y0 - pad)
            px1 = min(stamp_x1, x1 + pad)
            py1 = min(H, y1 + pad)
            pad_bbox = (px0, py0, px1 - px0, py1 - py0)
            cells.append(StampCell(row=r_i, col=c_i, bbox=bbox, pad_bbox=pad_bbox))
    return cells


def crop(img: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = bbox
    return img[y : y + h, x : x + w].copy()


def draw_cells(img: np.ndarray, cells: List[StampCell]) -> np.ndarray:
    out = img.copy()
    for c in cells:
        x, y, w, h = c.pad_bbox
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 140, 255), 2)
        cv2.putText(
            out,
            f"R{c.row}C{c.col}",
            (x + 3, y + 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 120, 220),
            1,
            cv2.LINE_AA,
        )
    return out
