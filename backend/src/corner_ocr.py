"""空角补齐：把定位到的单个角上数字放大后让模型只读这一个数字。

用途很窄但有效：整组识别时某个角给了 null（最典型是右上角被纸张折痕切断），
而该角确实有墨迹，就用这张放大图补一个值。

实测（assets/sample_page_hi.jpg，22 个可定位的左下角）：
- 单独读这一个数字 16/22 正确，但**不能用来覆盖已有的非空值**
  （会引入 4 个新错误，因为定位到的块有时是章框线段而不是数字）；
- 因此只用于填 null，且仅在「单枚知章」组上做（叠盖组的四角属于整组外轮廓，定位不可靠）。
"""

from __future__ import annotations

import base64
import os
from typing import Optional

import cv2

from deepseek_ocr import DEFAULT_BASE_URL, DEFAULT_MODEL, _extract_json, _norm_digit, load_dotenv_if_present

SYSTEM_DIGIT = """图中是方章某一角的手写数字局部放大图，通常只有一个手写阿拉伯数字，
笔画可能被旋转过任意角度。只输出 JSON：{"digit": 3}；
若这一格确实没有笔画（只有纸纹或章框线条）则输出 {"digit": null}。不要解释。"""


def _b64(img) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("编码失败")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def read_digit(crop, client=None, model: Optional[str] = None):
    """读单个角上的数字，返回 1-9 或 None。"""
    from openai import OpenAI

    if client is None:
        load_dotenv_if_present()
        key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not key:
            raise RuntimeError("未设置 DEEPSEEK_API_KEY")
        client = OpenAI(api_key=key, base_url=DEFAULT_BASE_URL)
    model = model or DEFAULT_MODEL
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_DIGIT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "读这个数字。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_b64(crop)}", "detail": "high"}},
                ],
            },
        ],
        temperature=0,
        max_tokens=40,
        extra_body={"thinking": {"type": "disabled"}},
    )
    try:
        parsed = _extract_json((resp.choices[0].message.content or "").strip())
    except Exception:
        return None
    return _norm_digit((parsed or {}).get("digit"))
