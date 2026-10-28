# 淮来学长 · 总管理后台

桌面 Web 后台（平台运营）。当前为**可运行静态落地版**，交互与设计原型一致，尚未对接 PMIS。

## 本地打开

```bash
cd admin
npx --yes serve -p 5180
# 浏览器打开 http://127.0.0.1:5180
```

或直接用浏览器打开 `index.html`。

## 模块

- 数据看板
- 学校管理
- 教师账号
- 家长 / 学生
- 订单与会员（凭证审核队列）
- 印章与编码（只读示意）
- 系统设置

## 下一步（接库）

与小程序共用 `test_table_hlxz_*`，独立运营登录；建议升级为 Vite + Vue，复用 `frontend` 的 `request` / 表常量口径。

设计稿备份：`../frontend/docs/prototypes/admin.html`
