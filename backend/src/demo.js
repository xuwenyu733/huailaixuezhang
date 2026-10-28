/**
 * 盖法可视化 + 模拟识别输出
 * 知章=蓝方，行章=黄圆；数字落在方章组外轮廓四角。
 */

const SealType = { ZHI: "zhi", XING: "xing" };

/** @typedef {{ type: string, cx: number, cy: number, rot?: number, z?: number }} Seal */
/** @typedef {{ id: number, name: string, desc: string, seals: Seal[], digits: boolean }} Method */

/** @type {Method[]} */
const METHODS = [
  {
    id: 1, name: "正向章（知章）", desc: "单枚蓝色方章，正向",
    digits: true,
    seals: [{ type: SealType.ZHI, cx: 0.5, cy: 0.5, rot: 0, z: 1 }],
  },
  {
    id: 2, name: "引导章（知章）", desc: "单枚蓝色方章，旋转180°",
    digits: true,
    seals: [{ type: SealType.ZHI, cx: 0.5, cy: 0.5, rot: 180, z: 1 }],
  },
  {
    id: 3, name: "改进章（知章）", desc: "引导章压在正向章左上",
    digits: true,
    seals: [
      { type: SealType.ZHI, cx: 0.78, cy: 0.78, rot: 0, z: 1 },
      { type: SealType.ZHI, cx: 0.42, cy: 0.42, rot: 180, z: 2 },
    ],
  },
  {
    id: 4, name: "知章二叠章", desc: "两枚正向方章斜向叠盖",
    digits: true,
    seals: [
      { type: SealType.ZHI, cx: 0.78, cy: 0.68, rot: 0, z: 1 },
      { type: SealType.ZHI, cx: 0.42, cy: 0.42, rot: 0, z: 2 },
    ],
  },
  {
    id: 5, name: "知章三叠章", desc: "三枚正向方章品字形",
    digits: true,
    seals: [
      { type: SealType.ZHI, cx: 0.32, cy: 0.78, rot: 0, z: 1 },
      { type: SealType.ZHI, cx: 0.88, cy: 0.78, rot: 0, z: 2 },
      { type: SealType.ZHI, cx: 0.60, cy: 0.32, rot: 0, z: 3 },
    ],
  },
  {
    id: 6, name: "行章", desc: "单枚黄色圆章",
    digits: false,
    seals: [{ type: SealType.XING, cx: 0.5, cy: 0.5, z: 1 }],
  },
  {
    id: 7, name: "行章二叠章", desc: "两枚圆章水平叠盖",
    digits: false,
    seals: [
      { type: SealType.XING, cx: 0.35, cy: 0.5, z: 1 },
      { type: SealType.XING, cx: 0.78, cy: 0.5, z: 2 },
    ],
  },
  {
    id: 8, name: "行章三叠章", desc: "三枚圆章品字形",
    digits: false,
    seals: [
      { type: SealType.XING, cx: 0.32, cy: 0.78, z: 1 },
      { type: SealType.XING, cx: 0.88, cy: 0.78, z: 2 },
      { type: SealType.XING, cx: 0.60, cy: 0.32, z: 3 },
    ],
  },
  {
    id: 9, name: "知行对章", desc: "方章压圆章",
    digits: true,
    seals: [
      { type: SealType.XING, cx: 0.68, cy: 0.55, z: 1 },
      { type: SealType.ZHI, cx: 0.38, cy: 0.45, rot: 0, z: 2 },
    ],
  },
  {
    id: 10, name: "知行对章二叠章", desc: "两对纵向叠盖",
    digits: true,
    seals: [
      { type: SealType.XING, cx: 0.72, cy: 0.82, z: 1 },
      { type: SealType.ZHI, cx: 0.38, cy: 0.72, rot: 0, z: 2 },
      { type: SealType.XING, cx: 0.72, cy: 0.28, z: 3 },
      { type: SealType.ZHI, cx: 0.38, cy: 0.18, rot: 0, z: 4 },
    ],
  },
  {
    id: 11, name: "知行对章三叠章", desc: "三对品字形叠盖",
    digits: true,
    seals: [
      { type: SealType.XING, cx: 0.32, cy: 0.88, z: 1 },
      { type: SealType.ZHI, cx: 0.18, cy: 0.78, rot: 0, z: 2 },
      { type: SealType.XING, cx: 0.98, cy: 0.88, z: 3 },
      { type: SealType.ZHI, cx: 0.84, cy: 0.78, rot: 0, z: 4 },
      { type: SealType.XING, cx: 0.65, cy: 0.32, z: 5 },
      { type: SealType.ZHI, cx: 0.51, cy: 0.22, rot: 0, z: 6 },
    ],
  },
];

const UNIT = 110; // 单章边长（像素，相对画布逻辑坐标）

function zhiBBox(seals) {
  const zhi = seals.filter((s) => s.type === SealType.ZHI);
  if (!zhi.length) return null;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const s of zhi) {
    const half = UNIT / 2;
    minX = Math.min(minX, s.cx * UNIT - half);
    minY = Math.min(minY, s.cy * UNIT - half);
    maxX = Math.max(maxX, s.cx * UNIT + half);
    maxY = Math.max(maxY, s.cy * UNIT + half);
  }
  return { minX, minY, maxX, maxY };
}

function drawZhi(ctx, cx, cy, rot = 0) {
  const s = UNIT;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate((rot * Math.PI) / 180);
  ctx.translate(-s / 2, -s / 2);

  // 方框
  ctx.strokeStyle = "#1e4a9c";
  ctx.lineWidth = 3.2;
  ctx.strokeRect(4, 4, s - 8, s - 8);

  // 四角斜线
  ctx.lineWidth = 2;
  const m = 14;
  [[m, m, m + 12, m + 12], [s - m, m, s - m - 12, m + 12],
   [m, s - m, m + 12, s - m - 12], [s - m, s - m, s - m - 12, s - m - 12]]
    .forEach(([x1, y1, x2, y2]) => {
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    });

  // 简化花+手
  ctx.fillStyle = "#1e4a9c";
  const fx = s / 2, fy = s / 2 - 8;
  for (let i = 0; i < 5; i++) {
    const a = (-90 + i * 72) * Math.PI / 180;
    ctx.beginPath();
    ctx.ellipse(fx + Math.cos(a) * 14, fy + Math.sin(a) * 14, 9, 7, a, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.beginPath();
  ctx.arc(fx, fy, 5, 0, Math.PI * 2);
  ctx.fill();

  // 手托
  ctx.beginPath();
  ctx.moveTo(fx - 18, fy + 28);
  ctx.quadraticCurveTo(fx - 8, fy + 12, fx, fy + 18);
  ctx.quadraticCurveTo(fx + 14, fy + 10, fx + 22, fy + 26);
  ctx.quadraticCurveTo(fx + 8, fy + 34, fx - 18, fy + 28);
  ctx.fill();

  ctx.restore();
}

function drawXing(ctx, cx, cy) {
  const r = UNIT / 2 - 4;
  ctx.save();
  ctx.translate(cx, cy);

  ctx.strokeStyle = "#d4a017";
  ctx.fillStyle = "rgba(212,160,23,0.12)";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.arc(0, 0, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.arc(0, 0, r - 8, 0, Math.PI * 2);
  ctx.stroke();

  // 三瓣花
  ctx.fillStyle = "#d4a017";
  for (let i = 0; i < 3; i++) {
    const a = (-90 + i * 120) * Math.PI / 180;
    ctx.beginPath();
    ctx.ellipse(Math.cos(a) * 14, Math.sin(a) * 14 - 6, 12, 10, a, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.beginPath();
  ctx.arc(0, -6, 4, 0, Math.PI * 2);
  ctx.fill();

  // 底部横条
  ctx.fillRect(-16, 18, 32, 6);

  ctx.restore();
}

function layoutOrigin(method, canvasW, canvasH) {
  // 估算内容包围盒，居中
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const s of method.seals) {
    const half = UNIT / 2;
    const x = s.cx * UNIT;
    const y = s.cy * UNIT;
    minX = Math.min(minX, x - half);
    minY = Math.min(minY, y - half);
    maxX = Math.max(maxX, x + half);
    maxY = Math.max(maxY, y + half);
  }
  // 为数字留边
  const pad = method.digits ? 36 : 16;
  minX -= pad; minY -= pad; maxX += pad; maxY += pad;
  const ox = (canvasW - (maxX - minX)) / 2 - minX;
  const oy = (canvasH - (maxY - minY)) / 2 - minY;
  return { ox, oy };
}

function drawMethod(ctx, method, digits, opts = {}) {
  const { width, height } = ctx.canvas;
  ctx.clearRect(0, 0, width, height);

  // 纸纹背景
  ctx.fillStyle = "#fffdf8";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(200,191,168,0.45)";
  ctx.lineWidth = 1;
  for (let y = 24; y < height; y += 28) {
    ctx.beginPath();
    ctx.moveTo(12, y);
    ctx.lineTo(width - 12, y);
    ctx.stroke();
  }

  const { ox, oy } = layoutOrigin(method, width, height);
  const sorted = [...method.seals].sort((a, b) => (a.z || 0) - (b.z || 0));

  for (const s of sorted) {
    const x = ox + s.cx * UNIT;
    const y = oy + s.cy * UNIT;
    if (s.type === SealType.ZHI) drawZhi(ctx, x, y, s.rot || 0);
    else drawXing(ctx, x, y);
  }

  // 四角数字：写在方章内侧四角（斜线旁）
  if (method.digits && digits) {
    const bb = zhiBBox(method.seals);
    if (bb) {
      const inset = UNIT * 0.16;
      const positions = {
        tl: [ox + bb.minX + inset, oy + bb.minY + inset + 6],
        tr: [ox + bb.maxX - inset, oy + bb.minY + inset + 6],
        bl: [ox + bb.minX + inset, oy + bb.maxY - inset + 6],
        br: [ox + bb.maxX - inset, oy + bb.maxY - inset + 6],
      };
      ctx.fillStyle = "#1e4a9c";
      ctx.font = "bold 22px 'DM Sans', sans-serif";
      ctx.textAlign = "center";
      for (const [k, v] of Object.entries(digits)) {
        if (v === null || v === undefined || v === "") continue;
        const [px, py] = positions[k];
        ctx.fillText(String(v), px, py);
      }

      if (opts.showGuides) {
        ctx.strokeStyle = "rgba(181,69,27,0.55)";
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(ox + bb.minX, oy + bb.minY, bb.maxX - bb.minX, bb.maxY - bb.minY);
        ctx.setLineDash([]);
      }
    }
  }
}

function readDigits() {
  const val = (id) => {
    const el = document.getElementById(id);
    if (!el || el.value === "") return null;
    return Number(el.value);
  };
  return {
    tl: val("dTL"),
    tr: val("dTR"),
    bl: val("dBL"),
    br: val("dBR"),
  };
}

function simulateDetect(method, digits) {
  const zhi = method.seals.filter((s) => s.type === SealType.ZHI).length;
  const xing = method.seals.filter((s) => s.type === SealType.XING).length;
  const conf = 0.88 + Math.random() * 0.1;
  return {
    method_id: method.id,
    method_name: method.name,
    confidence: conf,
    seal_count_zhi: zhi,
    seal_count_xing: xing,
    corner_digits: method.digits ? digits : { tl: null, tr: null, bl: null, br: null },
    note: method.digits
      ? "数字识别 ROI：方章组外接矩形四角外侧"
      : "纯行章盖法，无四角数字",
  };
}

function renderResult(det) {
  const dl = document.getElementById("resultDl");
  const corners = document.getElementById("resultCorners");
  const rows = [
    ["盖法编号", det.method_id],
    ["盖法名称", det.method_name],
    ["置信度", det.confidence.toFixed(3)],
    ["知章数量", det.seal_count_zhi],
    ["行章数量", det.seal_count_xing],
    ["说明", det.note],
  ];
  dl.innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");

  const labels = { tl: "左上", tr: "右上", bl: "左下", br: "右下" };
  corners.innerHTML = Object.entries(labels).map(([k, lab]) => {
    const v = det.corner_digits[k];
    const text = v === null || v === undefined ? "—" : v;
    return `<div class="corner-cell">${lab}：<strong>${text}</strong></div>`;
  }).join("");
}

function currentMethod() {
  const id = Number(document.getElementById("methodSelect").value);
  return METHODS.find((m) => m.id === id);
}

function refresh() {
  const method = currentMethod();
  const digits = readDigits();
  const canvas = document.getElementById("stage");
  const ctx = canvas.getContext("2d");
  drawMethod(ctx, method, digits, { showGuides: true });
  renderResult(simulateDetect(method, digits));

  document.querySelectorAll(".thumb").forEach((el) => {
    el.classList.toggle("active", Number(el.dataset.id) === method.id);
  });

  // 无数字盖法时禁用输入
  ["dTL", "dTR", "dBL", "dBR"].forEach((id) => {
    document.getElementById(id).disabled = !method.digits;
  });
}

function buildUI() {
  const sel = document.getElementById("methodSelect");
  sel.innerHTML = METHODS.map(
    (m) => `<option value="${m.id}">${m.id}. ${m.name}</option>`
  ).join("");

  const thumbs = document.getElementById("thumbs");
  thumbs.innerHTML = "";
  METHODS.forEach((m) => {
    const div = document.createElement("div");
    div.className = "thumb";
    div.dataset.id = String(m.id);
    const c = document.createElement("canvas");
    c.width = 160;
    c.height = 160;
    const span = document.createElement("span");
    span.textContent = `${m.id}. ${m.name}`;
    div.appendChild(c);
    div.appendChild(span);
    div.addEventListener("click", () => {
      sel.value = String(m.id);
      refresh();
    });
    thumbs.appendChild(div);
    const ctx = c.getContext("2d");
    drawMethod(ctx, m, m.digits ? { tl: 1, tr: 2, bl: 3, br: null } : null);
  });

  sel.addEventListener("change", refresh);
  document.getElementById("btnRender").addEventListener("click", refresh);
  document.getElementById("btnRandom").addEventListener("click", () => {
    ["dTL", "dTR", "dBL", "dBR"].forEach((id) => {
      const el = document.getElementById(id);
      if (el.disabled) return;
      el.value = Math.random() < 0.25 ? "" : String(1 + Math.floor(Math.random() * 7));
    });
    refresh();
  });
  ["dTL", "dTR", "dBL", "dBR"].forEach((id) => {
    document.getElementById(id).addEventListener("change", refresh);
  });

  refresh();
}

buildUI();
