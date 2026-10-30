# 印章叠盖识别服务（backend）

成长记录册「盖章处」识别：**蓝方知章** + **黄圆行章**，支持 11 种叠盖盖法，方章内侧四角填写数字。

引擎来自独立项目「印章识别」，已整体并入本仓库：**OpenCV 颜色分割定位 + DeepSeek 视觉逐组识别**。
小程序/H5 的采集页（`frontend/src/pages/scan/scan.vue`）通过 `/seal-api` 代理调用本服务。

## 启动

```bash
cd backend
# Windows
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py

# macOS / Linux
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python app.py
```

浏览器打开 **http://127.0.0.1:8765/**（上传识别）、**/demo**（盖法演示）。

密钥写在 `backend/.env`：

```
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-flash
```

可选环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `SEAL_MODE` | `cell` | `cell`=逐组裁切识别（推荐）；`page`=整页识别 |
| `SEAL_WORKERS` | `6` | 逐组识别并行线程数 |
| `SEAL_DIGIT_FILL` | `1` | 空角按手写墨迹补齐；`0` 关闭 |
| `SEAL_HINT_EST` | `0` | 是否把 CV 面积估数喂给模型（叠盖时偏低，默认关） |

## 接口

### `POST /api/recognize`

`multipart/form-data`，字段名 `file`（或 `image`），支持 png/jpg/webp/bmp。

返回核心结构（已与前端 `sealRecognize.ts` 对齐）：

```json
{
  "ok": true,
  "engine": "deepseek+cv",
  "mode": "cell",
  "layout": "record",
  "stamps": [
    {
      "index": 0, "row": 1,
      "method_id": 4, "method_name": "知章二叠章",
      "zhi": 2, "xing": 0,
      "orientation_deg": 0,
      "corner_digits": { "左上": 1, "右上": 3, "左下": 2, "右下": null },
      "confidence": 0.85,
      "bbox": [x, y, w, h],
      "crop_base64": "…"
    }
  ],
  "summary": { "groups": 27, "zhi_total": 29, "xing_total": 4 },
  "integrity": { "cells_detected": 27, "groups_returned": 27, "coverage": 1.0 },
  "degraded": [], "failed_cells": [], "dropped_groups": [],
  "warning": null,
  "result_image": "/output/result_xxx.jpg"
}
```

前端只取 `confidence` 最高的一组落库，并把 `degraded / dropped_groups / warning` 原样显示成采集页的黄色提示条。

### `GET /api/health`

逐项自检：密钥、模式、模型、OpenCV、8 个内部模块、样页、答案文件、上传目录。任一项不过即 `ok=false`。
加 `?probe=1` 会真发一次 1 token 请求，用来识别「余额耗尽但密钥还在」的情况。

上游 401/402/403 直接返回 HTTP 402 并中止，不逐组重试、不退回整页 —— 避免给出「看起来正常但少一半」的结果。

### `POST /api/ai/code-suggest`

自然语言（或语音转写）→ 编码建议，供前端「虚拟盖章 · AI 识别编码」使用。
提示词在 `prompts/ai_code_suggest.md`，走同一把 `DEEPSEEK_API_KEY`。

```bash
curl -s -X POST http://127.0.0.1:8765/api/ai/code-suggest \
  -H "Content-Type: application/json" \
  -d '{"text":"今天回家自己把作业写完，还检查了一遍","role":"parent"}'
```

返回：`code`（主线三位 `1-1-1`）、`level1/2/3`、`personal`（右下个性化位）、`digits[4]`、
`method`（正向章/引导章/改进章/行章/知行对章）、`stamp_type`、`quote`、`advice`、`confidence`、`reason`。

- 信息不足（如「孩子今天很高兴」）返回 `matched=false` 并说明缺什么，**不给编码**；
- 一级维度只接受 1–7，越界一律按未匹配处理，避免脏编码落库；
- 未配置密钥返回 400，上游 402 原样透传 402。

## 识别流程

1. **颜色分割**（`src/cv_detect.py`）：`B-R` 判蓝、`G-B` 判黄，亮度自适应阈值分离两种章；
2. **分组**：连通域 → 同行合并（只并「真重叠」或「并完 ≤ 1.45×单枚宽」）→ 残片贴近修补，得到「盖印单元」；
3. **版式判断**：每行一个单元且总数 ≤ 12 → 盖法说明页；否则记录页（两者提示词不同）；
4. **裁切放大**：bbox 外扩 26%（带进四角数字）并上采样到 640px；
5. **逐组识别**（`src/cell_ocr.py`）：只判这一组的知章数 / 行章数 / 朝向 / 四角数字；
6. **朝向校正**（`src/orient.py`）：说明页单枚知章组，用「花质心 → 手质心」连线判 180°；
7. **枚数复核**（`src/count_pass.py`）：说明页单独问一次枚数，并用模板相关区分改进章与知章二叠；
8. **盖法反推**：几枚知章 + 几枚行章 + 是否 180° → 1–11 号（`src/seal_methods.py`）；
9. **四角数字二次核对**（`src/corner_zoom.py`）：仅记录页执行，笔迹判定 + 双窗读数 + 多数投票，只在 `2↔3` 之间自动改，其余标 `review` 交人工。

## 两种章

| 类型 | 外观 | 数字 |
|------|------|------|
| 知章 | 蓝色方章（花+手） | 写在**内侧四角**（斜线旁）；叠盖取整组内角 |
| 行章 | 黄色圆章 | 无四角数字 |

## 11 种盖法

1. 正向章（知章）　2. 引导章（知章，180°）　3. 改进章（知章）　4. 知章二叠章　5. 知章三叠章
6. 行章　7. 行章二叠章　8. 行章三叠章　9. 知行对章　10. 知行对章二叠章　11. 知行对章三叠章

## 精度与已知局限

- 三张实测样页（`output/_cases/samples/`，2026-10-29 分组修正后）：定位 **38/38 组**，盖法 / 知章枚数 / 行章枚数全部 **38/38** 一致（p1 说明页 7 组、p2 记录页 27 组、p3 说明页 4 组），同一页连跑 3 次逐组结果完全一致。
- 原图实测（`assets/sample_page_hi.jpg`，连跑 4 次）：定位 27/27，整组正确 **25/27（92.6%）**，单角数字 **67/69（97.1%）**。
- **必须用手机原图**：768×1024 缩略图只能定位 22/27，第一行会整排丢失（`min(shape) < 900` 时接口会返回 `warning`）。
- 引导章 vs 正向章：记录页版式下未启用几何校正（手写数字与印章同为蓝墨会污染手形定位）。
- 改进章 vs 知章二叠：说明页需要本页存在「单枚蓝章」当模板，整页都是叠盖组时会跳过该判据。

### 分组阈值为什么要卡「重叠」而不是「间距」

原来同行合并的条件是 `gap < 0.30×单枚宽`，把「并排但不重叠」的两枚章也并成一组。实测页上因此出过三类错：

| 现象 | 后果 |
|---|---|
| 3、4 号两枚相邻正向章并成一组 | 模型读成「知章二叠」，有时读 1 枚有时读 2 枚（±1 波动就来自这里） |
| 5 号蓝章与 6 号黄行章并成一组 | 知行对章（9 号）盖法错判，知章多计 1 枚 |
| 10 号三叠与 11 号行章并成一组 | 行章整枚丢失，知章多计 1 枚 |

改成「水平真重叠（gap<0）或合并后宽度 ≤ 1.45×单枚宽」后，并排章保持分开、真叠盖仍然合并（实测二叠/三叠/知行对章全部靠 gap<0 命中）。另加残片修补：短边 ≤ 0.60×单枚宽的碎片（被印框或纸纹切开的半枚章）仍按近距离并回主块，避免一枚章被裁成两段。


## 历史模块

旧版整页识别流水线（`pipeline.py` / `orientation.py` / `table_cells.py` / `digit_ocr.py` / `recognize.py`）已移入 `src_legacy/`，不再被 `app.py` 引用，仅作留档。
