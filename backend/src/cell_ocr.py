"""单个盖印单元的视觉识别：只判这一组里有几枚知章/行章、是否旋转、四角数字。

相比整页识别，裁切放大后每枚章能占到 400+ 像素，角上数字从几个像素变成
几十像素，手写数字才读得出来。
"""

from __future__ import annotations

import base64
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import cv2

from deepseek_ocr import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    UpstreamFatal,
    _extract_json,
    _norm_digit,
    fatal_reason,
    load_dotenv_if_present,
)

SYSTEM_CELL = """你是成长记录册印章局部图识别助手。图片是一个盖章单元的局部放大图。
只统计画面中央这一组印章，忽略边缘可能露出的其他章。

规则：
- 蓝方=知章(zhi)，黄圆=行章(xing)。分别数出枚数（一格最多 3 枚同色）。
- corner_digits：蓝方章方框内侧四个角的手写数字（每条斜线外侧），
  只读整组最外轮廓的那一组四角数字；看不清或没有就填 null。
- 旋转：normal=花心下方的手形朝下（正向）；rotated=整体旋转180°（手形朝上、方框斜线方向相反）。

只输出 JSON，不要解释。"""

# 盖法说明页（一行一组示意图）：叠盖很多，必须在提示里点明「数章心」，
# 否则模型会把三叠当成一枚。记录页章与章分离，用上面那版更专注读数字。
SYSTEM_CELL_ILLUST = """你是成长记录册印章局部图识别助手。图片是一个盖章示意图的局部放大图。
只统计画面中央这一组印章，忽略边缘可能露出的其他章。

规则：
- 蓝方=知章(zhi)，黄圆=行章(xing)。分别数出枚数（一格最多 3 枚同色）。
  数枚数时数章心：几个花蕊就是几枚知章，几个圆环就是几枚行章；不要按油墨面积大小猜。
- corner_digits：蓝方章方框内侧四个角的手写数字（每条斜线外侧），
  只读整组最外轮廓的那一组四角数字；看不清或没有就填 null。
- 旋转：逐枚看知章的手形方向 —— 手形在花心下方=正向；手形在花心上方=整体旋转180°。
  rotation 填 normal 或 rotated。

只输出 JSON，不要解释。"""

STYLES = {"record": SYSTEM_CELL, "illustration": SYSTEM_CELL_ILLUST}

USER_CELL = (
    '输出 JSON：{"zhi":1,"xing":0,"rotation":"normal","corner_digits":'
    '{"左上":1,"右上":3,"左下":2,"右下":null},"confidence":0.9}'
)

RETRY_CELL = (
    "上一次判定这一组里没有任何印章。请再看一遍画面中央："
    "是否存在蓝色方章或黄色圆章？只要有就必须计数，并只输出 JSON。"
)


def _client():
    from openai import OpenAI

    load_dotenv_if_present()
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY")
    return OpenAI(api_key=key, base_url=DEFAULT_BASE_URL)


def _b64_png(img) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("裁剪图编码失败")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def parse_cell(raw: Dict[str, Any]) -> Dict[str, Any]:
    def _int(v) -> int:
        try:
            return max(0, min(3, int(v)))
        except (TypeError, ValueError):
            return 0

    cd = raw.get("corner_digits") or {}
    if not isinstance(cd, dict):
        cd = {}
    rot = raw.get("rotation")
    if rot is None:
        rot = "rotated" if raw.get("rotated_180") else "normal"
    conf = raw.get("confidence", 0.8)
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = 0.8

    zhi, xing = _int(raw.get("zhi")), _int(raw.get("xing"))
    if zhi and xing:  # 知行对章：两者应等量
        pass
    return {
        "zhi": zhi,
        "xing": xing,
        "rotation": str(rot),
        "rotation_deg": 180 if str(rot) == "rotated" else 0,
        "corner_digits": {
            "左上": _norm_digit(cd.get("左上")),
            "右上": _norm_digit(cd.get("右上")),
            "左下": _norm_digit(cd.get("左下")),
            "右下": _norm_digit(cd.get("右下")),
        },
        "confidence": round(conf, 3),
        "note": str(raw.get("note") or ""),
    }


def recognize_crop(crop, client=None, model: Optional[str] = None, hint: Optional[Dict[str, int]] = None,
                   style: str = "record") -> Dict[str, Any]:
    client = client or _client()
    model = model or DEFAULT_MODEL
    data_url = f"data:image/png;base64,{_b64_png(crop)}"
    system = STYLES.get(style, SYSTEM_CELL)

    text = USER_CELL
    if hint:
        text = (
            f"参考：颜色分割估计本组约 {hint.get('blue', 0)} 枚知章、{hint.get('yellow', 0)} 枚行章"
            "（叠盖遮挡会让估计偏小，仅作核对参考）。\n" + USER_CELL
        )

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
            ],
        },
    ]
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=800,
        extra_body={"thinking": {"type": "disabled"}},
    )
    parsed = _extract_json((resp.choices[0].message.content or "").strip())
    out = parse_cell(parsed)

    if out["zhi"] == 0 and out["xing"] == 0:  # 空结果兜底：追问一次
        messages = messages + [{"role": "user", "content": RETRY_CELL}]
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            max_tokens=800,
            extra_body={"thinking": {"type": "disabled"}},
        )
        out = parse_cell(_extract_json((resp.choices[0].message.content or "").strip()))
    return out


def recognize_crops(crops: List, workers: int = 6, hints: Optional[List[Dict[str, int]]] = None,
                    style: str = "record") -> List[Dict[str, Any]]:
    """逐组识别。遇到「无余额/密钥失效」直接抛 UpstreamFatal，不再逐组重复失败。

    否则一次 402 会变成「27 组都返回 0 枚 → 全部丢弃 → 退回整页 → 再失败」，
    前端最后只看到「未检测到印章」，完全误导。
    """
    if not crops:
        return []
    client = _client()
    model = DEFAULT_MODEL
    stop: Dict[str, Any] = {"fatal": None}

    def task(pair):
        i, c = pair
        hint = hints[i] if hints and i < len(hints) else None
        if stop["fatal"]:  # 已经确定不可用，剩下的别再发了
            return {"zhi": 0, "xing": 0, "rotation": "normal", "rotation_deg": 0,
                    "corner_digits": {"左上": None, "右上": None, "左下": None, "右下": None},
                    "confidence": 0.0, "note": "上游不可用，未调用", "error": stop["fatal"]}
        try:
            out = recognize_crop(c, client=client, model=model, hint=hint, style=style)
            if hint:
                out["cv_est"] = hint
            return out
        except Exception as e:  # noqa: BLE001
            fr = fatal_reason(e)
            if fr:
                stop["fatal"] = fr
            return {"zhi": 0, "xing": 0, "rotation": "normal", "rotation_deg": 0,
                    "corner_digits": {"左上": None, "右上": None, "左下": None, "右下": None},
                    "confidence": 0.0, "note": f"识别失败: {e}", "error": str(e)}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        out = list(ex.map(task, enumerate(crops)))
    if stop["fatal"]:
        raise UpstreamFatal(stop["fatal"])
    return out
