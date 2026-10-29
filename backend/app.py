"""
印章识别 Web 服务：上传图片 → DeepSeek 视觉识别。

用法：
  export DEEPSEEK_API_KEY=sk-xxx   # 或项目根目录 .env
  source .venv/bin/activate
  python app.py
然后打开 http://127.0.0.1:8765/
"""

from __future__ import annotations

import base64
import importlib
import os
import sys
import traceback
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cell_ocr import recognize_crops  # noqa: E402
import orient as orient_cv  # noqa: E402
from cv_detect import crop_group, detect_groups, to_original  # noqa: E402
from deepseek_ocr import UpstreamFatal, load_dotenv_if_present, recognize_with_deepseek  # noqa: E402
from seal_methods import classify_method  # noqa: E402

load_dotenv_if_present()

MODE = os.environ.get("SEAL_MODE", "cell").strip().lower()  # cell=逐组裁切识别, page=整页识别
CELL_WORKERS = int(os.environ.get("SEAL_WORKERS", "6"))
DIGIT_FILL = os.environ.get("SEAL_DIGIT_FILL", "1") not in ("0", "false", "False")  # 空角补齐
HINT_EST = os.environ.get("SEAL_HINT_EST", "0") not in ("0", "false", "False")  # 把 CV 面积估数喂给模型（默认关）

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
            "engine": "deepseek+cv" if MODE == "cell" else "deepseek",
            "mode": MODE,
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
        }
    )


@app.get("/api/health")
def api_health():
    """自检：把「跑得起来」和「跑得对」分开查，缺任何一项都直接说清楚。

    为什么要这个接口：以前密钥缺失/依赖缺失只会在识别时表现为「0 组」或退回整页，
    前端看到的是一张空结果，看不出是哪一环坏了。
    """
    load_dotenv_if_present()
    checks = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    add("api_key", bool(os.environ.get("DEEPSEEK_API_KEY", "").strip()),
        "已配置" if os.environ.get("DEEPSEEK_API_KEY", "").strip() else "未配置 DEEPSEEK_API_KEY")
    add("mode", MODE in ("cell", "page"), MODE)
    add("model", bool(os.environ.get("DEEPSEEK_MODEL", "").strip()), os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"))
    add("opencv", hasattr(cv2, "__version__"), getattr(cv2, "__version__", "缺失"))

    for mod in ("deepseek_ocr", "cv_detect", "cell_ocr", "corner_ocr", "corner_zoom",
                "count_pass", "orient", "seal_methods"):
        try:
            importlib.import_module(mod)
            add(f"module:{mod}", True)
        except Exception as e:  # noqa: BLE001
            add(f"module:{mod}", False, f"{type(e).__name__}: {e}")

    sample = ROOT / "assets" / "sample_page_hi.jpg"
    add("sample_page", sample.exists(), str(sample.name))
    truth = ROOT / "output" / "_verify" / "truth.json"
    add("truth", truth.exists(), str(truth.name))
    add("upload_dir", UPLOAD_DIR.is_dir(), str(UPLOAD_DIR))

    # 真实调一次上游（1 个 token）。不加这个探针，「有密钥」会被误当成「能用」，
    # 余额耗尽、密钥被停用时健康检查照样全绿，直到识别时才发现每个请求都 402。
    if request.args.get("probe") == "1":
        try:
            from cell_ocr import _client

            _client().chat.completions.create(
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                extra_body={"thinking": {"type": "disabled"}},
            )
            add("upstream", True, "在线，可计费调用")
        except Exception as e:  # noqa: BLE001
            add("upstream", False, f"{type(e).__name__}: {e}")

    return jsonify({
        "ok": all(c["ok"] for c in checks),
        "engine": "deepseek+cv" if MODE == "cell" else "deepseek",
        "mode": MODE,
        "checks": checks,
    })


@app.post("/api/recognize")
def api_recognize():
    load_dotenv_if_present()
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return jsonify(
            {
                "ok": False,
                "error": "未配置 DEEPSEEK_API_KEY。请在项目根目录 .env 写入密钥后重启服务。",
            }
        ), 400

    if "file" not in request.files and "image" not in request.files:
        sample = ROOT / "assets" / "sample_page_hi.jpg"
        if not sample.exists():
            sample = ROOT / "assets" / "sample_page.png"
        if request.form.get("sample") == "1" and sample.exists():
            return _recognize(sample)
        return jsonify({"ok": False, "error": "请上传图片"}), 400

    f = request.files.get("file") or request.files.get("image")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "空文件"}), 400

    suffix = Path(f.filename).suffix.lower() or ".png"
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        return jsonify({"ok": False, "error": "仅支持 png/jpg/webp/bmp"}), 400

    save_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    f.save(str(save_path))
    return _recognize(save_path)


def _recognize(image_path: Path):
    """按 SEAL_MODE 选择识别流程；cell 模式失败时退回整页识别。

    注意：退回**不再是静默的**。异常栈写进服务日志，同时把原因放进返回体的
    `degraded`，否则前端只会看到一份「看起来正常、其实走了另一条路」的结果。
    """
    degraded: list = []
    if MODE == "cell":
        try:
            return _recognize_cell(image_path, degraded)
        except UpstreamFatal as e:
            # 无余额/密钥失效：退到整页识别也一样会失败，只会白等几十秒
            app.logger.error("上游不可用，中止识别：%s", e)
            degraded.append({"stage": "upstream", "reason": str(e), "action": "已中止，未产出结果"})
            return jsonify({"ok": False, "error": f"DeepSeek 上游不可用：{e}", "degraded": degraded}), 402
        except Exception as e:  # noqa: BLE001
            app.logger.error("cell 模式异常，退回整页识别：%s\n%s", e, traceback.format_exc())
            degraded.append({
                "stage": "cell",
                "reason": f"{type(e).__name__}: {e}",
                "action": "已退回整页识别，四角数字可能不准",
            })
    return _recognize_deepseek(image_path, degraded)


def _preview_jpeg_b64(img, max_side: int = 1600) -> str:
    """整页预览：长边压到 1600 再编码，否则 4096 原图 base64 会有 2MB+。"""
    if img is not None and getattr(img, "size", 0):
        sc = max_side / max(img.shape[:2])
        if sc < 1:
            img = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 84])
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""


def _thumb_b64(img, side: int = 360) -> str:
    """每组一张小图，直接放进结果卡片，方便人眼立刻核对手写数字。"""
    if img is None or not getattr(img, "size", 0):
        return ""
    sc = side / max(img.shape[:2])
    small = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) if sc < 1 else img
    ok, buf = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""


def _annotate_deepseek(img, stamps: list):
    """在原图上画序号标签（DeepSeek 通常无 bbox）。"""
    vis = img.copy()
    h, w = vis.shape[:2]
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


def _annotate_cells(img, stamps: list):
    """在图上框出每个盖印单元，标注 序号:盖法 z知章数x行章数。"""
    vis = img.copy()
    h, w = vis.shape[:2]
    k = max(1, round(min(h, w) / 900))
    bar = max(36, int(h * 0.018))
    cv2.rectangle(vis, (0, 0), (w, bar), (26, 39, 68), -1)
    cv2.putText(
        vis,
        f"DeepSeek+CV  {len(stamps)} groups",
        (int(bar * 0.35), int(bar * 0.7)),
        cv2.FONT_HERSHEY_SIMPLEX,
        bar / 46.0,
        (255, 255, 255),
        k,
        cv2.LINE_AA,
    )
    for i, st in enumerate(stamps):
        bb = st.get("bbox") or []
        if len(bb) < 4:
            continue
        x, y, bw, bh = [int(v) for v in bb[:4]]
        color = (156, 74, 30) if st.get("zhi", 0) >= st.get("xing", 1) else (30, 170, 220)
        cv2.rectangle(vis, (x, y), (x + bw, y + bh), color, k + 1)
        label = f"{i + 1}:M{st.get('method_id')} z{st.get('zhi')}x{st.get('xing')}"
        cv2.putText(
            vis,
            label,
            (x, max(bar + 14, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            bar / 52.0,
            color,
            k,
            cv2.LINE_AA,
        )
    return vis


def _color_bbox(mask, box, scale):
    """在一组框内取某种颜色的紧包围盒，用于把并组拆成两条时给出各自的框。"""
    x0, y0, x1, y1 = box
    sub = mask[y0:y1, x0:x1]
    ys, xs = np.nonzero(sub)
    if len(xs) == 0:
        return list(to_original(box, scale))
    bx = (x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()) + 1, y0 + int(ys.max()) + 1)
    return list(to_original(bx, scale))


def _cv_orient(crop, zhi: int, xing: int, layout: str, cell: dict, degraded: list | None = None) -> None:
    """说明页版式下，单枚知章组用 CV 判朝向并覆盖模型结论。

    为什么要覆盖：正向章与引导章只差「手形在花心下方还是上方」，视觉模型对 180°
    基本不敏感（提示词里写「逐枚看手形」也只有偶尔生效）。而手形是整枚章里唯一有
    方向性的元素 —— 花心是一块、手形是独立的一块，两点连线的 dy 符号就足够定朝向。

    只在 illustration（盖法说明页）上做：记录页的四角手写数字与印章同为蓝墨，
    连通域里数字手写笔画会和手形混在一起（实测 27 组里会误判 14 组），不能用于覆盖。
    """
    if layout != "illustration" or zhi != 1 or xing != 0:
        return
    try:
        o = orient_cv.analyze(crop)
    except Exception as e:  # noqa: BLE001
        app.logger.warning("朝向判定失败，保留模型结果：%s", e)
        if degraded is not None:
            degraded.append({"stage": "cv_orient", "reason": f"{type(e).__name__}: {e}",
                             "action": "沿用模型给的朝向"})
        return
    cell["orient_cv_dy"] = round(o.dy_ratio, 3)
    if o.rotated is None:
        return
    want = "rotated" if o.rotated else "normal"
    cell["rotation_model"] = cell.get("rotation")
    if want != str(cell.get("rotation")):
        cell["rotation"] = want
        cell["rotation_deg"] = 180 if o.rotated else 0
        cell["rotation_fixed_by"] = "cv"


def _refine_digits(img, stamps, workers: int = CELL_WORKERS):
    """四角数字二次核对：空角补齐 + 左下角受限复核。

    实测结论（record 页 69 个有数字的角）：
    - 整组读 21/23（左下角），单角放大读最多 16/23 —— 放大读**不能整体替换**整组读；
    - 放大读唯一稳定赢过整组读的地方，是手写的 2 和 3（笔画侧倒时整组容易把 3 读成 2）；
    - 5、2 这类会被放大图带偏（5 侧倒后很像 3），所以自动改数只允许在 {2,3} 之间，
      其他分歧一律标 `digit_review` 交给人，不静默改。
    所有改动都写进 `digit_fixed` / `digit_filled_detail`，UI 上能看到原值。
    读角过程中抛出的异常不再吞掉，逐条进 `errors`，由调用方汇总进 `degraded`。
    """
    import corner_zoom as CZ

    targets = [s for s in stamps if s.get("zhi", 0) >= 1 and s.get("bbox")]
    if not targets:
        return 0, 0, [], None
    stop: dict = {}  # 上游致命错误（无余额/密钥失效）共享给所有线程，命中即停

    def task(s):
        bbox = s["bbox"]
        cd = dict(s.get("corner_digits") or {})
        out = {"filled": [], "fixed": [], "review": [], "zoom_bl": "", "errors": []}

        def read(name, idx):
            if stop.get("fatal"):
                return None, None, []
            errs: list = []
            try:
                val, crop_a, votes = CZ.read_corner3(img, bbox, name, errors=errs, stop=stop)
            except Exception as e:  # noqa: BLE001
                val, crop_a, votes = None, None, []
                errs.append(f"{type(e).__name__}: {e}")
            for msg in errs:
                out["errors"].append({"index": idx, "corner": name, "reason": msg})
            return val, crop_a, votes

        # 左下角：三窗多数（0.45 / 0.65 外偏，不一致再加 0.55 内移窗裁决）
        val, crop_a, votes = read("左下", s.get("index"))
        cur = cd.get("左下")
        if crop_a is not None:
            out["zoom_bl"] = _thumb_b64(crop_a, 200)
        if val is not None:
            if cur is None:
                cd["左下"] = val
                out["filled"].append({"corner": "左下", "from": None, "to": val})
            elif cur != val and {cur, val} <= {2, 3}:
                out["fixed"].append({"corner": "左下", "from": cur, "to": val})
                cd["左下"] = val
            elif cur != val:
                # 放大读与整组读不同，但不在已知可救的 {2,3} 混淆对里 → 不猜
                out["review"].append({"corner": "左下", "group": cur, "candidates": votes})
        elif cur is not None and len(set(votes)) > 1:
            out["review"].append({"corner": "左下", "group": cur, "candidates": votes})

        # 其余两角：只在原值为空时补（右下角按本册规则恒为空，不补）
        for name in ("左上", "右上"):
            if cd.get(name) is not None:
                continue
            v, _c, votes = read(name, s.get("index"))
            if v is not None:
                cd[name] = v
                out["filled"].append({"corner": name, "from": None, "to": v})
        out["corner_digits"] = cd
        return out

    n_fill = n_fix = 0
    errors: list = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for s, out in zip(targets, ex.map(task, targets)):
            s["corner_digits"] = out["corner_digits"]
            if out["zoom_bl"]:
                s["zoom_bl"] = out["zoom_bl"]
            if out["filled"]:
                s["digit_filled_detail"] = out["filled"]
            if out["fixed"]:
                s["digit_fixed"] = out["fixed"]
            if out["review"]:
                s["digit_review"] = out["review"]
            errors.extend(out["errors"])
            n_fill += len(out["filled"])
            n_fix += len(out["fixed"])
    return n_fill, n_fix, errors, stop.get("fatal")


def _ambiguity_review(stamps, layout: str) -> None:
    """把「机器判不出来、需要人看一眼」的组显式标出来，不静默给结论。"""
    for s in stamps:
        notes = list(s.get("review") or [])
        z, x = s.get("zhi", 0), s.get("xing", 0)
        if layout == "illustration" and z == 2 and x == 0:
            notes.append("两枚知章叠盖：若其中一枚旋转 180° 则是 3 号改进章，否则是 4 号知章二叠，请核对朝向")
        if layout == "illustration" and z >= 2 and x >= 2:
            notes.append("知行对章多叠：行章易被蓝章压住，请核对行章枚数")
        if s.get("digit_review"):
            for r in s["digit_review"]:
                cands = "/".join("空" if c is None else str(c) for c in r["candidates"])
                uniq = {c for c in r["candidates"] if c is not None}
                if len(uniq) == 1:
                    notes.append(f"{r['corner']}放大读 {cands.split('/')[0]} 与整组读 {r['group']} 不同，"
                                 f"已保留整组值，请核对")
                else:
                    notes.append(f"{r['corner']}放大读自相矛盾（{cands}），"
                                 f"已保留整组值 {r['group']}，请核对")
        if notes:
            s["review"] = notes


def _recognize_cell(image_path: Path, degraded: list | None = None):
    """逐组裁切识别：CV 定位每个盖印单元 → 放大 → 模型只判这一组。

    每条可能降级的路径都写进 `degraded`（异常栈同时进日志）。返回体里另有
    `failed_cells` / `dropped_groups` / `integrity` 三个账本，保证「少了一组」
    「某一组没识别成功」不会被 `zip` 截断或 `continue` 悄悄吞掉。
    """
    degraded = degraded if degraded is not None else []
    img = cv2.imread(str(image_path))
    if img is None:
        return jsonify({"ok": False, "error": "无法读取图片（文件损坏或格式不支持）"}), 400

    groups, work, _blue, _yellow, scale = detect_groups(img)
    if not groups:
        degraded.append({"stage": "detect", "reason": "颜色分割未定位到任何印章单元",
                         "action": "已退回整页识别"})
        return _recognize_deepseek(image_path, degraded)

    # 裁切为空时不能直接 filter 掉：groups 与 crops 必须一一对应，否则后面 zip
    # 会把组的坐标错配到别的组上（这是一个真实踩过的隐性 bug）。
    pairs = [(g, crop_group(work, g)) for g in groups]
    empty_idx = [i for i, (_g, c) in enumerate(pairs) if not c.size]
    if empty_idx:
        degraded.append({"stage": "crop", "reason": f"{len(empty_idx)} 个单元的裁切图为空",
                         "action": "这些单元未送模型，其余继续"})
        pairs = [(g, c) for g, c in pairs if c.size]
    if not pairs:
        degraded.append({"stage": "crop", "reason": "全部单元裁切为空",
                         "action": "已退回整页识别"})
        return _recognize_deepseek(image_path, degraded)
    groups = [p[0] for p in pairs]
    crops = [p[1] for p in pairs]

    # 版式判断：盖法说明页是「一行一组示意图」，记录页是「一行五六组盖章」。
    # 前者叠盖密集，要用「数章心」版提示词才数得准；后者用常规版更专注读四角数字。
    row_counts = Counter(g.row for g in groups)
    layout = "illustration" if max(row_counts.values()) == 1 and len(groups) <= 12 else "record"
    # 颜色分割的面积估数在叠盖时明显偏低（二叠常估成 1、三叠估成 2），
    # 实测把它当提示喂给模型会让模型跟着少数，故默认不传；仅留作结果里的 cv_est 参考。
    hints = None
    if HINT_EST:
        hints = [{"blue": g.est_blue, "yellow": g.est_yellow} for g in groups]
    cells = recognize_crops(crops, workers=CELL_WORKERS, hints=hints, style=layout)
    if len(cells) != len(crops):
        degraded.append({"stage": "recognize",
                         "reason": f"模型返回 {len(cells)} 条，裁切 {len(crops)} 组，条数不一致",
                         "action": "只保留能对上的前若干组"})

    failed_cells = [
        {"group": i, "bbox": list(to_original(groups[i].bbox, scale)), "reason": str(c.get("error"))}
        for i, c in enumerate(cells)
        if c.get("error")
    ]
    if failed_cells:
        degraded.append({"stage": "recognize", "reason": f"{len(failed_cells)} 组单组识别调用失败",
                         "action": "这些组的枚数/数字不可信，已列入 failed_cells"})

    # 说明页版式：枚数再单独问一次（主调用要同时读数字，会把三叠数成二叠），
    # 并用模板相关判「改进章 vs 知章二叠」。记录页不动 —— 那边枚数本来就全对。
    count_fixed = mixed_fixed = 0
    if layout == "illustration" and cells:
        try:
            import count_pass

            cnt = count_pass.color_guard(count_pass.count_groups(work, groups, workers=CELL_WORKERS), groups)
            missing = sum(1 for v in cnt if v is None)
            if missing:
                degraded.append({"stage": "count_pass",
                                 "reason": f"{missing} 组独立计数没拿到结果",
                                 "action": "这些组沿用主调用的枚数"})
            for c, got in zip(cells, cnt):
                if got is None:
                    continue
                cur = (int(c.get("zhi") or 0), int(c.get("xing") or 0))
                if got != cur:
                    c["count_model"] = f"{cur[0]}/{cur[1]}"
                    c["zhi"], c["xing"] = got
                    c["count_fixed_by"] = "count_pass"
                    count_fixed += 1
            for i in count_pass.mixed_flags(work, groups, _blue, cnt):
                cells[i]["rotation"] = "rotated"
                cells[i]["rotation_deg"] = 180  # 盖法按 rotated 归类，卡片朝向必须跟着变，否则自相矛盾
                cells[i]["rotation_model"] = "mixed_tpl"
                cells[i]["rotation_fixed_by"] = "tpl"
                mixed_fixed += 1
        except Exception as e:  # noqa: BLE001
            app.logger.error("枚数复核失败：%s\n%s", e, traceback.format_exc())
            degraded.append({"stage": "count_pass", "reason": f"{type(e).__name__}: {e}",
                             "action": "沿用主调用的枚数"})

    stamps = []
    dropped = []
    adjustments = []
    areas = sorted(g.w * g.h for g in groups)
    med_area = areas[len(areas) // 2] if areas else 0
    for gi, (g, c, crop) in enumerate(zip(groups, cells, crops)):
        zhi, xing = int(c.get("zhi") or 0), int(c.get("xing") or 0)
        if not zhi and not xing:
            # 模型读不出枚数：不静默丢弃，记进 dropped_groups 并给出「误检 / 漏检」倾向，
            # 让人一眼分得清「这组本来就没章」和「这组是真章但没读出来」。
            ratio = round((g.w * g.h) / med_area, 2) if med_area else 1.0
            verdict = (
                f"疑似 CV 误检（面积仅中位组的 {ratio:.0%}，多为页边阴影/纸纹）"
                if ratio < 0.45
                else "疑似漏检（面积接近正常组，请人工确认）"
            )
            dropped.append({
                "group": gi,
                "bbox": list(to_original(g.bbox, scale)),
                "blue_px": g.blue_px,
                "yellow_px": g.yellow_px,
                "cv_est": {"blue": g.est_blue, "yellow": g.est_yellow},
                "area_ratio": ratio,
                "verdict": verdict,
                "reason": "模型判为 0 枚" if not c.get("error") else f"识别失败：{c.get('error')}",
            })
            continue

        _cv_orient(crop, zhi, xing, layout, c, degraded)
        raw = f"{zhi}/{xing}"
        combos = [(zhi, xing)]
        if zhi and xing:
            if abs(zhi - xing) >= 2:
                # 数量差太多：多半是两个相邻的章被并进了一组，拆成两条记录，避免丢数
                combos = [(zhi, 0), (0, xing)]
                adjustments.append({"group": gi, "type": "split_merged", "raw": raw,
                                    "result": "拆为 2 条记录"})
            else:
                pairs_n = min(zhi, xing, 3)  # 知行对章按规则成对
                if pairs_n != zhi or pairs_n != xing:
                    adjustments.append({"group": gi, "type": "pair_normalize", "raw": raw,
                                        "result": f"按对章归一为 {pairs_n}/{pairs_n}"})
                combos = [(pairs_n, pairs_n)]

        for cz, cx in combos:
            mid, mname = classify_method(cz, cx, c.get("rotation", "normal"))
            if len(combos) > 1:  # 并组已拆开，各条按自己那种颜色的紧包围盒出框
                bbox = _color_bbox(_blue if cz else _yellow, g.bbox, scale)
            else:
                bbox = list(to_original(g.bbox, scale))
            stamps.append(
                {
                    "index": len(stamps),
                    "row": g.row,
                    "col": -1,
                    "method_id": mid,
                    "method_name": mname,
                    "zhi": cz,
                    "xing": cx,
                    "raw_counts": raw,
                    "count_model": c.get("count_model"),
                    "count_fixed_by": c.get("count_fixed_by"),
                    "orientation": c.get("rotation_deg"),
                    "orientation_deg": c.get("rotation_deg"),
                    "rotation_model": c.get("rotation_model"),
                    "rotation_fixed_by": c.get("rotation_fixed_by"),
                    "orient_cv_dy": c.get("orient_cv_dy"),
                    "corner_digits": c.get("corner_digits") if cz else None,
                    "confidence": c.get("confidence"),
                    "bbox": bbox,
                    "cv_est": c.get("cv_est") or {"blue": g.est_blue, "yellow": g.est_yellow},
                    "crop_side": int(min(crop.shape[:2])) if crop.size else 0,
                    "crop_base64": _thumb_b64(crop) if crop.size else "",
                    "note": c.get("note") or "",
                }
            )

    if not any(s["zhi"] or s["xing"] for s in stamps):
        degraded.append({"stage": "recognize", "reason": "全部单元都被判为 0 枚",
                         "action": "已退回整页识别"})
        return _recognize_deepseek(image_path, degraded)

    filled = corrected = 0
    digit_errors: list = []
    # 四角数字只存在于记录页（手写的行为编码）。说明页是盖法图例，四角本来就空白，
    # 在这里补数只会补出「幽灵数字」（界面上一片 — — 1 —），还会白花十几次调用。
    if DIGIT_FILL and layout == "record":
        try:
            filled, corrected, digit_errors, fatal = _refine_digits(img, stamps)
        except Exception as e:  # noqa: BLE001
            app.logger.error("四角数字二次核对失败：%s\n%s", e, traceback.format_exc())
            degraded.append({"stage": "digit_refine", "reason": f"{type(e).__name__}: {e}",
                             "action": "只用主调用一次读出的四角数字"})
        else:
            if fatal:
                degraded.append({"stage": "digit_refine", "reason": f"上游拒绝：{fatal}",
                                 "action": "已停止角窗复核，保留主调用的读数"})
            elif digit_errors:
                degraded.append({"stage": "digit_refine",
                                 "reason": f"{len(digit_errors)} 次角窗读取出错（接口或裁切问题）",
                                 "action": "出错的那个角保留主调用的读数",
                                 "detail": digit_errors[:8]})
    elif layout != "record":
        for s in stamps:
            s["corner_digits"] = None
    _ambiguity_review(stamps, layout)

    rot_fixed = sum(1 for s in stamps if s.get("rotation_fixed_by") in ("cv", "tpl"))

    vis = _annotate_cells(img, stamps)
    out_name = f"result_{uuid.uuid4().hex[:10]}.jpg"
    cv2.imwrite(str(ROOT / "output" / out_name), vis)

    return jsonify(
        {
            "ok": True,
            "engine": "deepseek+cv",
            "mode": "cell",
            "layout": layout,
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
            "page_type": "B" if layout == "illustration" else "A",
            "page_note": f"逐组裁切识别：定位到 {len(groups)} 个盖印单元"
            + ("（按盖法说明页版式）" if layout == "illustration" else "")
            + (f"，按章面图案校正朝向 {rot_fixed} 处" if rot_fixed else "")
            + (f"，按独立计数修正枚数 {count_fixed} 处" if count_fixed else "")
            + (f"，按模板相关认出改进章 {mixed_fixed} 处" if mixed_fixed else "")
            + (f"，补全空角数字 {filled} 处" if filled else "")
            + (f"，按放大图校正数字 {corrected} 处" if corrected else ""),
            "attempts": 1,
            "digit_filled": filled,
            "count_corrected": count_fixed,
            "digit_corrected": corrected,
            "review_groups": sum(1 for s in stamps if s.get("review")),
            "integrity": {
                "cells_detected": len(groups),
                "cells_cropped": len(crops),
                "cells_recognized": len(cells),
                "groups_returned": len(stamps),
                "groups_dropped": len(dropped),
                "cells_failed": len(failed_cells),
                "coverage": round(len(stamps) / max(1, len(groups)), 3),
            },
            "degraded": degraded,
            "failed_cells": failed_cells,
            "dropped_groups": dropped,
            "adjustments": adjustments,
            "summary": {
                "cells": len(stamps),
                "groups": len(stamps),
                "zhi_total": sum(s["zhi"] for s in stamps),
                "xing_total": sum(s["xing"] for s in stamps),
            },
            "warning": (
                "原图分辨率偏低，角上数字可能读不准，建议上传手机原图"
                if min(img.shape[:2]) < 900
                else None
            ),
            "stamps": stamps,
            "result_image": f"/output/{out_name}",
            "preview_base64": _preview_jpeg_b64(vis),
        }
    )


def _recognize_deepseek(image_path: Path, degraded: list | None = None):
    degraded = degraded if degraded is not None else []
    try:
        stamps, meta = recognize_with_deepseek(image_path)
    except UpstreamFatal as e:
        app.logger.error("整页识别上游不可用：%s", e)
        degraded.append({"stage": "upstream", "reason": str(e), "action": "已中止，未产出结果"})
        return jsonify({"ok": False, "error": f"DeepSeek 上游不可用：{e}", "degraded": degraded}), 402
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e), "degraded": degraded}), 400
    except Exception as e:  # noqa: BLE001
        app.logger.error("整页识别失败：%s\n%s", e, traceback.format_exc())
        return jsonify({"ok": False, "error": f"DeepSeek 识别失败: {e}", "degraded": degraded}), 500

    img = cv2.imread(str(image_path))
    if img is None:
        return jsonify({"ok": False, "error": "无法读取图片", "degraded": degraded}), 400

    vis = _annotate_deepseek(img, stamps)
    out_name = f"result_{uuid.uuid4().hex[:10]}.jpg"
    out_path = ROOT / "output" / out_name
    cv2.imwrite(str(out_path), vis)

    return jsonify(
        {
            "ok": True,
            "engine": "deepseek",
            "model": meta.get("model"),
            "page_type": meta.get("page_type"),
            "page_note": meta.get("page_note"),
            "attempts": meta.get("attempts"),
            "usage": meta.get("usage"),
            "fallback_from": "cell" if degraded else None,
            "degraded": degraded,
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


if __name__ == "__main__":
    load_dotenv_if_present()
    has_key = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
    print("印章识别已启动 → http://127.0.0.1:8765/")
    print("设计演示     → http://127.0.0.1:8765/demo")
    print(f"引擎         → DeepSeek 视觉（密钥{'已配置' if has_key else '未配置，请设置 DEEPSEEK_API_KEY'}）")
    app.run(host="127.0.0.1", port=8765, debug=False)
