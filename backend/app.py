"""
印章识别 Web 服务：上传图片 → DeepSeek 视觉识别（默认）/ 本地 OpenCV。

用法：
  export DEEPSEEK_API_KEY=sk-xxx   # 或项目根目录 .env
  source .venv/bin/activate
  python app.py
然后打开 http://127.0.0.1:8765/
"""

from __future__ import annotations

import base64
import os
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

import cv2
from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from deepseek_ocr import load_dotenv_if_present, recognize_with_deepseek  # noqa: E402
from pipeline import draw_page, run_page  # noqa: E402

load_dotenv_if_present()

UPLOAD_DIR = ROOT / "output" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=None)


@app.get("/")
def index():
    return send_from_directory(ROOT, "recognize.html")


@app.get("/demo")
def demo_page():
    return send_from_directory(ROOT, "index.html")


@app.get("/src/<path:filename>")
def src_files(filename: str):
    return send_from_directory(ROOT / "src", filename)


@app.get("/assets/<path:filename>")
def asset_files(filename: str):
    return send_from_directory(ROOT / "assets", filename)


@app.get("/output/<path:filename>")
def output_files(filename: str):
    return send_from_directory(ROOT / "output", filename)


@app.get("/api/status")
def api_status():
    load_dotenv_if_present()
    has_key = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
    return jsonify(
        {
            "ok": True,
            "deepseek_configured": has_key,
            "default_engine": "deepseek" if has_key else "local",
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
        }
    )


@app.post("/api/recognize")
def api_recognize():
    engine = (request.form.get("engine") or request.args.get("engine") or "").strip().lower()
    if engine not in {"deepseek", "local"}:
        load_dotenv_if_present()
        engine = "deepseek" if os.environ.get("DEEPSEEK_API_KEY", "").strip() else "local"

    if "file" not in request.files and "image" not in request.files:
        sample = ROOT / "assets" / "sample_page.png"
        if request.form.get("sample") == "1" and sample.exists():
            return _recognize_path(sample, engine)
        return jsonify({"ok": False, "error": "请上传图片"}), 400

    f = request.files.get("file") or request.files.get("image")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "空文件"}), 400

    suffix = Path(f.filename).suffix.lower() or ".png"
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        return jsonify({"ok": False, "error": "仅支持 png/jpg/webp/bmp"}), 400

    save_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    f.save(str(save_path))
    return _recognize_path(save_path, engine)


def _preview_jpeg_b64(img) -> str:
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""


def _recognize_local(image_path: Path):
    try:
        page = run_page(image_path)
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"本地识别失败: {e}"}), 500

    img = cv2.imread(str(image_path))
    if img is None:
        return jsonify({"ok": False, "error": "无法读取图片"}), 400

    vis = draw_page(img, page)
    out_name = f"result_{uuid.uuid4().hex[:10]}.jpg"
    out_path = ROOT / "output" / out_name
    cv2.imwrite(str(out_path), vis)

    stamps = [asdict(s) for s in page.stamps]
    return jsonify(
        {
            "ok": True,
            "engine": "local",
            "summary": {
                "cells": page.cells,
                "groups": len(page.stamps),
                "zhi_total": sum(s.zhi for s in page.stamps),
                "xing_total": sum(s.xing for s in page.stamps),
            },
            "stamp_column": list(page.stamp_column),
            "table_top": page.table_top,
            "stamps": stamps,
            "result_image": f"/output/{out_name}",
            "preview_base64": _preview_jpeg_b64(vis),
        }
    )


def _annotate_deepseek(img, stamps: list):
    """在原图上画序号标签（DeepSeek 通常无 bbox）。"""
    vis = img.copy()
    h, w = vis.shape[:2]
    # 右上角说明条
    cv2.rectangle(vis, (0, 0), (w, 36), (26, 39, 68), -1)
    cv2.putText(
        vis,
        f"DeepSeek  {len(stamps)} groups",
        (12, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    # 若模型给了 bbox 则画框
    for i, st in enumerate(stamps):
        bb = st.get("bbox")
        if not bb or not isinstance(bb, (list, tuple)) or len(bb) < 4:
            continue
        x, y, bw, bh = [int(v) for v in bb[:4]]
        color = (30, 74, 156) if st.get("zhi", 0) >= st.get("xing", 0) else (20, 160, 212)
        cv2.rectangle(vis, (x, y), (x + bw, y + bh), color, 2)
        label = f"{i + 1}:{st.get('method_id', '?')}"
        cv2.putText(vis, label, (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return vis


def _recognize_deepseek(image_path: Path):
    try:
        stamps, meta = recognize_with_deepseek(image_path)
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"DeepSeek 识别失败: {e}"}), 500

    img = cv2.imread(str(image_path))
    if img is None:
        return jsonify({"ok": False, "error": "无法读取图片"}), 400

    vis = _annotate_deepseek(img, stamps)
    out_name = f"result_{uuid.uuid4().hex[:10]}.jpg"
    out_path = ROOT / "output" / out_name
    cv2.imwrite(str(out_path), vis)

    return jsonify(
        {
            "ok": True,
            "engine": "deepseek",
            "model": meta.get("model"),
            "page_note": meta.get("page_note"),
            "usage": meta.get("usage"),
            "summary": {
                "cells": len(stamps),
                "groups": len(stamps),
                "zhi_total": sum(int(s.get("zhi") or 0) for s in stamps),
                "xing_total": sum(int(s.get("xing") or 0) for s in stamps),
            },
            "stamps": stamps,
            "result_image": f"/output/{out_name}",
            "preview_base64": _preview_jpeg_b64(vis),
        }
    )


def _recognize_path(image_path: Path, engine: str):
    if engine == "deepseek":
        return _recognize_deepseek(image_path)
    return _recognize_local(image_path)


if __name__ == "__main__":
    load_dotenv_if_present()
    has_key = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
    print("印章识别已启动 → http://127.0.0.1:8765/")
    print("设计演示     → http://127.0.0.1:8765/demo")
    print(
        f"默认引擎     → {'DeepSeek 视觉' if has_key else '本地 OpenCV（未检测到 DEEPSEEK_API_KEY）'}"
    )
    app.run(host="127.0.0.1", port=8765, debug=False)
