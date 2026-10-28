"""
印章盖法定义：两种章 + 11 种叠盖方式 + 方章四角数字规则。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class SealType(str, Enum):
    ZHI = "知章"  # 蓝色方章
    XING = "行章"  # 黄色圆章


class Corner(str, Enum):
    TL = "左上"
    TR = "右上"
    BL = "左下"
    BR = "右下"


@dataclass
class SealInstance:
    """单枚印章在组合中的几何描述（相对坐标系）。"""

    seal_type: SealType
    cx: float  # 中心 x，单位：章宽
    cy: float  # 中心 y，单位：章高
    rotation_deg: float = 0.0  # 0=正向，180=引导章
    scale: float = 1.0
    z_index: int = 0  # 越大越靠上


@dataclass
class StampMethod:
    """一种盖法。"""

    id: int
    name: str
    description: str
    seals: List[SealInstance]
    # 方章四角数字：只对方章有意义；叠盖时数字写在「外轮廓」四角
    supports_corner_digits: bool = True
    # 数字应落在整组方章外接矩形的四角（而不是每一枚）
    digits_on_group_bbox: bool = True


# 相对坐标：以单枚方章边长 = 1
# 圆章直径约等于方章边长


METHODS: List[StampMethod] = [
    StampMethod(
        id=1,
        name="正向章（知章）",
        description="单枚蓝色方章，正向",
        seals=[SealInstance(SealType.ZHI, 0.5, 0.5, 0, z_index=1)],
    ),
    StampMethod(
        id=2,
        name="引导章（知章）",
        description="单枚蓝色方章，旋转180°",
        seals=[SealInstance(SealType.ZHI, 0.5, 0.5, 180, z_index=1)],
    ),
    StampMethod(
        id=3,
        name="改进章（知章）",
        description="两枚方章：引导章压在正向章左上角",
        seals=[
            SealInstance(SealType.ZHI, 0.85, 0.85, 0, z_index=1),
            SealInstance(SealType.ZHI, 0.45, 0.45, 180, z_index=2),
        ],
    ),
    StampMethod(
        id=4,
        name="知章二叠章",
        description="两枚正向方章水平/斜向叠盖",
        seals=[
            SealInstance(SealType.ZHI, 0.85, 0.70, 0, z_index=1),
            SealInstance(SealType.ZHI, 0.45, 0.45, 0, z_index=2),
        ],
    ),
    StampMethod(
        id=5,
        name="知章三叠章",
        description="三枚正向方章品字形叠盖",
        seals=[
            SealInstance(SealType.ZHI, 0.35, 0.85, 0, z_index=1),
            SealInstance(SealType.ZHI, 0.95, 0.85, 0, z_index=2),
            SealInstance(SealType.ZHI, 0.65, 0.35, 0, z_index=3),
        ],
    ),
    StampMethod(
        id=6,
        name="行章",
        description="单枚黄色圆章",
        seals=[SealInstance(SealType.XING, 0.5, 0.5, 0, z_index=1)],
        supports_corner_digits=False,
    ),
    StampMethod(
        id=7,
        name="行章二叠章",
        description="两枚圆章水平叠盖",
        seals=[
            SealInstance(SealType.XING, 0.35, 0.5, 0, z_index=1),
            SealInstance(SealType.XING, 0.85, 0.5, 0, z_index=2),
        ],
        supports_corner_digits=False,
    ),
    StampMethod(
        id=8,
        name="行章三叠章",
        description="三枚圆章品字形叠盖",
        seals=[
            SealInstance(SealType.XING, 0.35, 0.85, 0, z_index=1),
            SealInstance(SealType.XING, 0.95, 0.85, 0, z_index=2),
            SealInstance(SealType.XING, 0.65, 0.35, 0, z_index=3),
        ],
        supports_corner_digits=False,
    ),
    StampMethod(
        id=9,
        name="知行对章",
        description="一枚方章压在一枚圆章上",
        seals=[
            SealInstance(SealType.XING, 0.70, 0.55, 0, z_index=1),
            SealInstance(SealType.ZHI, 0.40, 0.45, 0, z_index=2),
        ],
    ),
    StampMethod(
        id=10,
        name="知行对章二叠章",
        description="两对方章+圆章纵向叠盖",
        seals=[
            SealInstance(SealType.XING, 0.75, 0.85, 0, z_index=1),
            SealInstance(SealType.ZHI, 0.40, 0.75, 0, z_index=2),
            SealInstance(SealType.XING, 0.75, 0.25, 0, z_index=3),
            SealInstance(SealType.ZHI, 0.40, 0.15, 0, z_index=4),
        ],
    ),
    StampMethod(
        id=11,
        name="知行对章三叠章",
        description="三对方章+圆章品字形叠盖",
        seals=[
            SealInstance(SealType.XING, 0.35, 0.95, 0, z_index=1),
            SealInstance(SealType.ZHI, 0.20, 0.85, 0, z_index=2),
            SealInstance(SealType.XING, 1.05, 0.95, 0, z_index=3),
            SealInstance(SealType.ZHI, 0.90, 0.85, 0, z_index=4),
            SealInstance(SealType.XING, 0.70, 0.35, 0, z_index=5),
            SealInstance(SealType.ZHI, 0.55, 0.25, 0, z_index=6),
        ],
    ),
]


@dataclass
class CornerDigits:
    """方章四周（四角）填写的数字，缺省为 None 表示该角无数字。"""

    tl: Optional[int] = None
    tr: Optional[int] = None
    bl: Optional[int] = None
    br: Optional[int] = None

    def as_dict(self) -> dict:
        return {
            "左上": self.tl,
            "右上": self.tr,
            "左下": self.bl,
            "右下": self.br,
        }

    def filled_count(self) -> int:
        return sum(v is not None for v in (self.tl, self.tr, self.bl, self.br))


@dataclass
class DetectedStamp:
    """识别结果：一种盖法 + 方章四角数字。"""

    method_id: int
    method_name: str
    confidence: float
    seal_count_zhi: int
    seal_count_xing: int
    corner_digits: CornerDigits = field(default_factory=CornerDigits)
    bbox: Optional[Tuple[int, int, int, int]] = None  # x,y,w,h


def group_bbox(seals: List[SealInstance], size: float = 1.0) -> Tuple[float, float, float, float]:
    """返回相对坐标系下的外接矩形 (min_x, min_y, max_x, max_y)。"""
    half = size / 2
    xs, ys = [], []
    for s in seals:
        # 方章按正方形，圆章按外接正方形近似
        xs.extend([s.cx - half * s.scale, s.cx + half * s.scale])
        ys.extend([s.cy - half * s.scale, s.cy + half * s.scale])
    return min(xs), min(ys), max(xs), max(ys)


def corner_digit_anchors(
    seals: List[SealInstance], offset: float = 0.12
) -> dict:
    """
    叠盖时数字写在整组方章外轮廓四角外侧。
    返回四个角的相对坐标。
    """
    zhi = [s for s in seals if s.seal_type == SealType.ZHI]
    if not zhi:
        return {}
    min_x, min_y, max_x, max_y = group_bbox(zhi)
    return {
        Corner.TL: (min_x - offset, min_y - offset),
        Corner.TR: (max_x + offset, min_y - offset),
        Corner.BL: (min_x - offset, max_y + offset),
        Corner.BR: (max_x + offset, max_y + offset),
    }


def method_by_id(method_id: int) -> StampMethod:
    for m in METHODS:
        if m.id == method_id:
            return m
    raise KeyError(f"未知盖法 id={method_id}")


def summarize_feasibility() -> str:
    return """
可行性结论：可以实现。

推荐流水线：
1. 颜色分离：HSV 分离蓝(知章)/黄(行章)
2. 形状检测：方章=近似正方形轮廓；行章=近似圆形轮廓
3. 实例聚类：按重叠距离聚类 → 得到一组「盖印单元」
4. 盖法分类：根据 知章数/行章数/相对位置/旋转 → 匹配 1~11 号盖法
5. 四角数字 OCR：在方章组外接矩形四角外侧小 ROI 做手写数字识别

难点与对策：
- 叠盖遮挡 → 用连通域+模板匹配计数，不必完美分割每一枚
- 引导章旋转 → 模板同时匹配 0°/180°
- 手写数字贴边 → 外扩 ROI + 轻量 OCR（PaddleOCR / EasyOCR）
- 纸张表格线干扰 → 先裁「盖章处」单元格再识别
""".strip()
