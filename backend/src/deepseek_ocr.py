"""DeepSeek 视觉 API：按印章规则识别盖章页，返回结构化 stamps。"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "deepseek_seal_ocr.md"

DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
DEFAULT_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

SYSTEM_FALLBACK = """你是成长记录册盖章识别助手。只根据图片与规则输出 JSON，不要解释过程。

规则摘要：
- 蓝方=知章（读内侧四角手写数字）；黄圆=行章（四角全 null）。
- 盖法 1–11：正向/引导(180°)/改进/知章二叠/知章三叠/行章/行章二叠/行章三叠/知行对章/知行对章二叠/知行对章三叠。
- 数字在方章内侧四角（斜线旁）；常只填三个角；看不清填 null。
- 叠盖按整组外轮廓读一组四角数字。
- 读序：盖章处列内，上→下，左→右。

输出 schema：
{"stamps":[{"row":0,"col":0,"method_id":1,"method_name":"正向章（知章）","zhi":1,"xing":0,"orientation_deg":0,"corner_digits":{"左上":1,"右上":3,"左下":2,"右下":null},"confidence":0.9}]}"""

USER_PROMPT = (
    "请识别这张成长记录册「盖章处」图片。"
    "直接输出合法 JSON（含 stamps 数组），不要 markdown，不要解释。"
)


def load_dotenv_if_present() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        return SYSTEM_FALLBACK
    text = PROMPT_PATH.read_text(encoding="utf-8")
    m = re.search(r"## 系统提示\s*\n+(.+?)(?:\n## |\Z)", text, re.S)
    if not m:
        return SYSTEM_FALLBACK
    body = m.group(1).strip()
    # 去掉文档里的 json 示例围栏外多余说明时可保留全文
    return body or SYSTEM_FALLBACK


def _mime_for(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/png",
    }.get(ext, "image/jpeg")


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("模型返回为空")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"stamps": data}
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
    raise ValueError("无法从模型回复中解析 JSON")


def _norm_digit(v: Any) -> Optional[int]:
    if v is None or v == "" or v == "—" or v == "-":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        n = int(v)
        return n if 0 <= n <= 9 else None
    s = str(v).strip()
    if s.isdigit() and len(s) == 1:
        return int(s)
    return None


def normalize_stamps(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = raw.get("stamps")
    if items is None and isinstance(raw.get("data"), dict):
        items = raw["data"].get("stamps")
    if not isinstance(items, list):
        raise ValueError("JSON 缺少 stamps 数组")

    out: List[Dict[str, Any]] = []
    for i, st in enumerate(items):
        if not isinstance(st, dict):
            continue
        corners_in = st.get("corner_digits") or {}
        if not isinstance(corners_in, dict):
            corners_in = {}
        corners = {
            "左上": _norm_digit(corners_in.get("左上")),
            "右上": _norm_digit(corners_in.get("右上")),
            "左下": _norm_digit(corners_in.get("左下")),
            "右下": _norm_digit(corners_in.get("右下")),
        }
        ori = st.get("orientation_deg", st.get("orientation"))
        if ori is not None:
            try:
                ori = int(ori)
            except (TypeError, ValueError):
                ori = None

        method_id = st.get("method_id")
        try:
            method_id = int(method_id) if method_id is not None else 0
        except (TypeError, ValueError):
            method_id = 0

        zhi = st.get("zhi", 0)
        xing = st.get("xing", 0)
        try:
            zhi = int(zhi)
        except (TypeError, ValueError):
            zhi = 0
        try:
            xing = int(xing)
        except (TypeError, ValueError):
            xing = 0

        conf = st.get("confidence", 0.8)
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.8

        row = st.get("row", -1)
        col = st.get("col", -1)
        try:
            row = int(row)
        except (TypeError, ValueError):
            row = -1
        try:
            col = int(col)
        except (TypeError, ValueError):
            col = -1

        out.append(
            {
                "index": i,
                "row": row,
                "col": col,
                "method_id": method_id,
                "method_name": str(st.get("method_name") or f"盖法{method_id}"),
                "zhi": zhi,
                "xing": xing,
                "orientation": ori,
                "orientation_deg": ori,
                "corner_digits": corners,
                "confidence": round(conf, 3),
                "bbox": st.get("bbox"),
            }
        )
    return out


def recognize_with_deepseek(image_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """调用 DeepSeek 视觉接口。返回 (stamps, meta)。"""
    load_dotenv_if_present()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "未设置 DEEPSEEK_API_KEY。请在项目根目录创建 .env 写入 DEEPSEEK_API_KEY=sk-xxx，或 export 后重启服务。"
        )

    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("缺少 openai 包，请执行: pip install openai") from e

    image_path = Path(image_path)
    raw_bytes = image_path.read_bytes()
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    mime = _mime_for(image_path)
    data_url = f"data:{mime};base64,{b64}"

    client = OpenAI(api_key=api_key, base_url=DEFAULT_BASE_URL)
    model = DEFAULT_MODEL

    # deepseek-flash 默认开启 thinking，长页会把 max_tokens 耗尽在推理里，content 为空
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"},
                    },
                ],
            },
        ],
        temperature=0.1,
        max_tokens=8192,
        extra_body={"thinking": {"type": "disabled"}},
    )

    msg = resp.choices[0].message
    content = (msg.content or "").strip()
    if not content:
        reasoning = getattr(msg, "reasoning_content", None) or ""
        finish = resp.choices[0].finish_reason
        raise RuntimeError(
            f"模型返回为空（finish={finish}）。"
            + ("推理占满了输出额度，已应关闭 thinking；请重试。" if finish == "length" else "")
            + (f" reasoning 片段: {reasoning[:120]}…" if reasoning else "")
        )

    parsed = _extract_json(content)
    stamps = normalize_stamps(parsed)
    meta = {
        "engine": "deepseek",
        "model": model,
        "page_note": parsed.get("page_note"),
        "usage": {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
            "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            "total_tokens": getattr(resp.usage, "total_tokens", None),
        },
    }
    return stamps, meta
