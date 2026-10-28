# 淮来学长

伴随式学生成长评价系统。

| 目录 | 说明 |
|------|------|
| `frontend/` | UniApp 小程序（家长 / 教师 / 学校端） |
| `backend/` | 桌面印章识别 Flask 服务（默认端口 8765） |
| `admin/` | 平台总管理后台（静态落地版，`npm run dev` → 5180） |

## 前端

```bash
cd frontend
npm install
npm run dev:h5          # H5
npm run dev:mp-weixin   # 微信开发者工具打开 dist/dev/mp-weixin
```

## 后端（印章识别）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 配置 DEEPSEEK_API_KEY 后：
python app.py           # http://127.0.0.1:8765/
```

H5 开发时，前端 Vite 已将 `/seal-api` 代理到本服务。
