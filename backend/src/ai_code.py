"""自然语言 → ZZE 编码建议。

用途：虚拟章不再要求家长自己翻编码表，直接描述孩子行为（或语音转写结果），
由模型按《AI辅助交互使用》四（四）标准输出格式给出编码 + 原文引用 + 对话建议。

与 deepseek_ocr 共用同一把 DEEPSEEK_API_KEY 与 base_url，不额外引入依赖。
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from deepseek_ocr import (  # noqa: F401  同目录模块
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    _extract_json,
    fatal_reason,
    load_dotenv_if_present,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "ai_code_suggest.md"

# 文档第六部分：七大维度，编号即编码第 1 位
DIM_NAMES: Dict[int, str] = {
    1: "格物",
    2: "致知",
    3: "诚意",
    4: "正心",
    5: "体育",
    6: "美育",
    7: "劳育",
}

# 章型映射：模型只输出中文章法名，这里转成前端可直接用的字段
METHOD_MAP: Dict[str, Dict[str, str]] = {
    "正向章": {"stamp_type": "know", "know_kind": "正向章"},
    "引导章": {"stamp_type": "know", "know_kind": "引导章"},
    "改进章": {"stamp_type": "know", "know_kind": "改进章"},
    "行章": {"stamp_type": "do", "know_kind": ""},
    "知行对章": {"stamp_type": "combo", "know_kind": ""},
}

SYSTEM_FALLBACK = """你是 ZZE 教育评价体系的编码匹配助手。只根据用户描述的行为判定一个编码，输出 JSON。

七大维度（编码第 1 位）：1 格物、2 致知、3 诚意、4 正心、5 体育、6 美育、7 劳育。
四角编码：左上=一级维度(1-7)、右上=二级指标(1-9)、左下=三级行为(1-9)、右下=个性化(0-9，无则 0)。
输出格式：{"matched":true,"level1":1,"level2":1,"level3":1,"personal":0,"code":"1-1-1",
"method":"正向章","quote":"","advice":"","confidence":0.8,"reason":""}
禁止编造编码；信息不足时 matched 置 false 并在 reason 说明缺什么。不做心理诊断与人格定性。"""

USER_TEMPLATE = """孩子行为描述：{text}
{extra}
请只输出 JSON。"""


def load_system_prompt() -> str:
    """取 markdown 里「## 系统提示」到下一个「## 」之间的正文。"""
    if not PROMPT_PATH.exists():
        return SYSTEM_FALLBACK
    text = PROMPT_PATH.read_text(encoding="utf-8")
    m = re.search(r"## 系统提示\s*\n+(.+?)(?:\n## |\Z)", text, re.S)
    return (m.group(1).strip() if m else "") or SYSTEM_FALLBACK


def _as_int(v: Any, lo: int, hi: int) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        m = re.search(r"\d", str(v))
        if not m:
            return None
        n = int(m.group(0))
    return n if lo <= n <= hi else None


def _split_code(code: str) -> List[Optional[int]]:
    """把 1-1-1 / 111 / 1.1.1 拆成三位。"""
    parts = re.split(r"[^\d]+", str(code or "").strip())
    parts = [p for p in parts if p]
    if len(parts) < 3 and parts and len(parts[0]) >= 3:
        parts = list(parts[0][:3])
    return [_as_int(p, 0, 9) for p in parts[:3]]


def normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
    """把模型输出收敛成前端可用的固定结构，非法值一律降级而不是抛错。"""
    matched = bool(payload.get("matched", True))
    lv = _split_code(payload.get("code", ""))
    lv = (lv + [None, None, None])[:3]
    level1 = _as_int(payload.get("level1"), 1, 7) or lv[0]
    level2 = _as_int(payload.get("level2"), 1, 9) or lv[1] or 1
    level3 = _as_int(payload.get("level3"), 1, 9) or lv[2] or 1
    personal = _as_int(payload.get("personal"), 0, 9)
    if personal is None:
        personal = 0

    method = str(payload.get("method") or "正向章").strip()
    for key in METHOD_MAP:
        if key in method:
            method = key
            break
    else:
        method = "正向章"

    try:
        conf = float(payload.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))

    if level1 is not None and level1 not in DIM_NAMES:
        # 一级维度只有 1–7，越界一律判为「没匹配上」，不让脏编码落库
        level1 = None
    if level1 is None:
        matched = False

    advice = str(payload.get("advice") or "").strip()[:120]
    quote = str(payload.get("quote") or "").strip()[:300]
    reason = str(payload.get("reason") or "").strip()[:200]

    return {
        "matched": matched,
        "code": f"{level1}-{level2}-{level3}" if level1 else "",
        "level1": level1,
        "level2": level2,
        "level3": level3,
        "personal": personal,
        "digits": [level1 if level1 else 0, level2, level3, personal],
        "dim_name": DIM_NAMES.get(level1 or 0, ""),
        "method": method,
        "stamp_type": METHOD_MAP[method]["stamp_type"],
        "know_kind": METHOD_MAP[method]["know_kind"],
        "quote": quote,
        "advice": advice,
        "confidence": round(conf, 3),
        "reason": reason,
        "alternatives": payload.get("alternatives") or [],
    }


def suggest_code(
    text: str,
    *,
    grade: str = "",
    scene: str = "",
    role: str = "parent",
) -> Dict[str, Any]:
    """调用模型给出编码建议。上游不可用会抛 UpstreamFatal 由路由层转 402/502。"""
    load_dotenv_if_present()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY，请在 backend/.env 配置后重启服务")

    try:
        from openai import OpenAI
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("缺少 openai 包，请先 pip install -r requirements.txt") from e

    extra_bits = []
    if grade:
        extra_bits.append(f"年龄/年级：{grade}")
    if scene:
        extra_bits.append(f"发生场景：{scene}")
    if role == "teacher":
        extra_bits.append("盖章人：教师（学校端，注意学科与观测点）")
    extra = ("\n".join(extra_bits) + "\n") if extra_bits else ""

    client = OpenAI(api_key=api_key, base_url=DEFAULT_BASE_URL)
    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": USER_TEMPLATE.format(text=text.strip(), extra=extra)},
        ],
        temperature=0,
        max_tokens=1024,
        extra_body={"thinking": {"type": "disabled"}},
    )
    content = (resp.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("模型返回为空，请重试")

    data = _extract_json(content)
    out = normalize(data)
    out["source_text"] = text.strip()
    return out
