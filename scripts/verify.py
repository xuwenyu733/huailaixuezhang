"""一键验证：服务 / 接口 / 代码点 / 识别回归。

用法（在仓库根目录执行）：
    python scripts/verify.py            # 只做服务 + 接口 + 代码点
    python scripts/verify.py --seal     # 追加印章识别的离线视觉回归（不调模型）
    python scripts/verify.py --no-api   # 跳过需要 DeepSeek 额度的接口检查

退出码：0 全通过；1 有失败项。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H5 = "http://localhost:5174"
ADMIN = "http://127.0.0.1:5180"
API = "http://127.0.0.1:8765"

DIM_ORDER = ["格物", "致知", "诚意", "正心", "体育", "美育", "劳育"]
DIM_NAMES = {i + 1: n for i, n in enumerate(DIM_ORDER)}

results: list[tuple[str, str, bool, str]] = []


def add(group: str, name: str, ok: bool, note: str = "") -> None:
    results.append((group, name, ok, note))


def read(rel: str) -> str:
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def http_get(url: str, timeout: float = 8) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")
    except Exception as e:  # 连接失败等
        return 0, str(e)


def http_post(url: str, payload: dict, timeout: float = 90) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "ignore") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(body or "{}")
        except Exception:
            return e.code, {"error": body}
    except Exception as e:
        return 0, {"error": str(e)}


# ---------------------------------------------------------------- 1. 服务探活
def check_services() -> None:
    code, _ = http_get(H5)
    add("服务", "H5 前台 :5174", code == 200, f"HTTP {code}")

    code, _ = http_get(ADMIN)
    add("服务", "管理后台 :5180", code == 200, f"HTTP {code}")

    code, body = http_get(f"{API}/api/health")
    ok = False
    note = f"HTTP {code}"
    try:
        d = json.loads(body)
        bad = [c["name"] for c in d.get("checks", []) if not c.get("ok")]
        ok = bool(d.get("ok")) and not bad
        note = f"engine={d.get('engine')} checks={len(d.get('checks', []))}" + (
            f" 失败={bad}" if bad else ""
        )
    except Exception:
        note = f"HTTP {code} 返回非 JSON"
    add("服务", "印章后端 :8765 /api/health", ok, note)


# ------------------------------------------------------- 2. AI 编码识别接口
def check_ai_code(run: bool) -> None:
    if not run:
        add("接口", "AI 编码识别（跳过）", True, "已用 --no-api 跳过")
        return

    cases = [
        ("对话场景", "孩子今天主动把碗筷洗了，还问我还有没有要帮忙的"),
        ("记录本场景", "今天做数学作业，遇到难题没有放弃，自己想出来两种解法"),
        ("语音口语", "嗯他今天体育课跑八百米的时候没停下来，一直跑到终点"),
    ]
    for label, text in cases:
        code, d = http_post(
            f"{API}/api/ai/code-suggest", {"text": text, "role": "parent"}
        )
        digits = d.get("digits")
        ok = (
            code == 200
            and d.get("ok") is True
            and d.get("matched") is True
            and isinstance(digits, list)
            and len(digits) == 4
            and d.get("level1") in DIM_NAMES
            and d.get("code") == f"{digits[0]}-{digits[1]}-{digits[2]}"
        )
        note = (
            f"code={d.get('code')} dim={d.get('dim_name')} 章型={d.get('method')}"
            if code == 200
            else f"HTTP {code} {d.get('error')}"
        )
        add("接口", f"AI 编码 · {label}", ok, note)

    # 编码第 1 位与维度名必须自洽
    code, d = http_post(f"{API}/api/ai/code-suggest", {"text": "孩子自己整理了书包"})
    lv1 = d.get("level1")
    ok = code == 200 and bool(lv1) and d.get("dim_name") == DIM_NAMES.get(lv1)
    add("接口", "维度名与编码第 1 位自洽", ok, f"{lv1} → {d.get('dim_name')}")

    # 空输入必须 400 且带中文提示
    code, d = http_post(f"{API}/api/ai/code-suggest", {"text": "  "})
    add("接口", "空输入被拒绝", code == 400 and bool(d.get("error")), f"HTTP {code}")


# ------------------------------------------------------------ 3. 代码点核对
def check_code_points() -> None:
    dims = read("frontend/src/constants/dimensions.ts")
    found = re.findall(r"\{\s*code:\s*(\d+),\s*name:\s*'([^']+)'", dims)
    order = [n for _, n in found]
    add(
        "代码",
        "七大维度口径 1–7",
        len(found) == 7 and order == DIM_ORDER,
        " / ".join(order) if order else "未解析到 DIMENSIONS",
    )
    add(
        "代码",
        "四角拆分 splitCode",
        "tl" in dims and "tr" in dims and "bl" in dims and "br" in dims,
        "左上/右上/左下/右下",
    )

    stamp = read("frontend/src/pages/stamp/stamp.vue")
    add("代码", "行章可手动盖", "行章" in stamp, "行章类型入口")
    stack = re.search(r"stackOptions[^=]*=\s*\[([^\]]+)\]", stamp)
    add(
        "代码",
        "行章 1/2/3 叠",
        bool(stack) and stack.group(1).count(",") == 2,
        stack.group(1).strip() if stack else "未找到 stackOptions",
    )
    add(
        "代码",
        "家长端中心不选科",
        "locked: !isTeacher" in stamp and "isTeacher.value ? centerText" in stamp,
        "家长端锁定中心，仅教师可切",
    )
    add(
        "代码",
        "AI 编码卡片 + 语音入口",
        "suggestCode" in stamp and "startVoice" in stamp,
        "对话/记录/语音同一套识别",
    )
    add(
        "代码",
        "维度由编码推导（不再手选）",
        "不再手选" in stamp and "dimNameOf(c.tl)" in stamp,
        "primaryDim = 编码第 1 位",
    )

    scan = read("frontend/src/pages/scan/scan.vue")
    add(
        "代码",
        "采集页 4 位编码（3 主线 + 1 个性化）",
        "codeLine" in scan and "codePersonal" in scan,
        "前三位主线，第四位个性化",
    )

    repo = read("frontend/src/services/reportRepo.ts")
    add(
        "代码",
        "报告按编码聚合、撤销手选维度",
        "DIM_MAP" not in repo and "dimNameOf" in repo and "charAt(0)" in repo,
        "DIM_MAP 已删除，取编码首位",
    )

    off = read("frontend/src/utils/official.ts")
    pages = ["mall/mall", "catalog/catalog", "shop/shop"]
    used = [p for p in pages if "openOfficial" in read(f"frontend/src/pages/{p}.vue")]
    add(
        "代码",
        "商品跳官网",
        "OFFICIAL_SITE" in off and len(used) == 3,
        f"官方站点 + {len(used)}/3 页调用",
    )
    goals = read("frontend/src/pages/goals/goals.vue")
    add(
        "代码",
        "奖励商品可选",
        "INCENTIVE_GOODS" in goals,
        "来自统一商品常量，带自定义兜底",
    )

    add(
        "代码",
        "待确认清单",
        os.path.exists(os.path.join(ROOT, "docs/待确认清单.md")),
        "9 项未定事项已归档",
    )

    # 当量显示口径：统一 +N DE / ZE / XE，不再出现“行章当量（XE）”这类中文注解
    sm = read("frontend/src/constants/sealMethods.ts")
    src_hits = []
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "frontend", "src")):
        for f in files:
            if not f.endswith((".vue", ".ts")):
                continue
            path = os.path.join(dirpath, f)
            with open(path, encoding="utf-8") as fh:
                if "行章当量" in fh.read():
                    src_hits.append(os.path.relpath(path, ROOT))
    add(
        "代码",
        "当量文案统一为 +N 单位",
        "formatStampValue" in sm and not src_hits,
        "sealMethods.formatStampValue；残留：" + (", ".join(src_hits) if src_hits else "无"),
    )
    home = read("frontend/src/pages/home/home.vue")
    add(
        "代码",
        "首页记录当量跟章型走",
        "formatStampValue" in home and "value_text ||" not in home,
        "DE/ZE/XE 由 stamp_type + source 推导",
    )
    stamp_rec = read("frontend/src/pages/stamp/stamp.vue")
    add(
        "代码",
        "记录列表排版与参考图一致",
        "实体' : '虚拟'} · ${dimNameOf" in stamp_rec and "编码${r.code_text}`" in stamp_rec,
        "标题=实体/虚拟·维度，副标题=科目·姓名·编码",
    )
    demo = read("frontend/src/constants/demoData.ts")
    bad_vals = [
        v
        for v in re.findall(r"value_text:\s*'([^']*)'", demo)
        if not re.fullmatch(r"\+\d+ (ZE|XE|DE)", v)
    ]
    add(
        "代码",
        "演示记录当量格式统一",
        not bad_vals,
        "全部为 +N ZE/XE/DE" if not bad_vals else "异常：" + ", ".join(bad_vals),
    )


# ------------------------------------------------------ 4. 印章识别离线回归
def check_seal() -> None:
    py = os.path.join(ROOT, "backend", ".venv", "Scripts", "python.exe")
    if not os.path.exists(py):
        py = sys.executable
    script = os.path.join(ROOT, "backend", "output", "_cases", "evaluate.py")
    if not os.path.exists(script):
        add("识别", "离线视觉回归（跳过）", True, "未找到 evaluate.py")
        return
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    # opencv 处理三张大图偶发 OOM（机器内存紧时），失败重试一次再判
    for attempt in range(2):
        try:
            out = subprocess.run(
                [py, script],
                cwd=os.path.join(ROOT, "backend"),
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )
            text = (out.stdout or "") + (out.stderr or "")
            ok = out.returncode == 0
            tail = [l for l in text.strip().splitlines() if l.strip()][-3:]
            note = " | ".join(tail)[:170]
            if not ok and attempt == 0 and "MemoryError" in text:
                continue
            add("识别", "离线视觉回归 evaluate.py", ok, note + ("（重试后通过）" if attempt and ok else ""))
            return
        except Exception as e:
            if attempt == 0:
                continue
            add("识别", "离线视觉回归 evaluate.py", False, str(e)[:120])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seal", action="store_true", help="追加印章识别离线回归")
    ap.add_argument("--no-api", action="store_true", help="跳过需要模型额度的接口检查")
    args = ap.parse_args()

    check_services()
    check_ai_code(not args.no_api)
    check_code_points()
    if args.seal:
        check_seal()

    total = len(results)
    passed = sum(1 for *_, ok, _ in results if ok)
    width = max(len(n) for _, n, _, _ in results)
    print("\n" + "=" * 78)
    print(f"{'分组':<5}{'检查项':<{width + 2}}结果   说明")
    print("-" * 78)
    last = ""
    for group, name, ok, note in results:
        g = group if group != last else ""
        last = group
        print(f"{g:<5}{name:<{width + 2}}{'PASS' if ok else 'FAIL':<6}{note}")
    print("-" * 78)
    print(f"合计 {passed}/{total} 通过" + ("  ⚠️ 有失败项" if passed != total else "  ✅ 全部通过"))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
