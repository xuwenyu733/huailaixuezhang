# 淮来学长（Uniapp）

伴随式学生成长评价系统小程序。当前阶段已完成：

- 家长端登录 / 注册（协议确认、手机号密码、微信授权入口）
- 基础推荐关系（专属推荐码、注册绑定、缴费发 50 积分、积分抵扣年费）
- 通过 **uniapp 专用 request** 调用 PMIS（wiidu）接口读写数据

## PMIS 建表

请先按 `docs/PMIS建表清单.md` 在自定义表单页新建 2 张表（**只新建，不动其它表**）。

## 接口用法

```ts
import request from '@/utils/request'

const sql = 'select * from test_table_hlxz_parent where isDel = 0'
const res = await request.post(
  'mysql/getDataListBySql.jsp',
  { sqlstring: [sql] },
  { noVerify: true, noAuth: true },
)

// 写入改用 updateInfo.jsp
```

## 运行

在本目录（`frontend/`）执行：

```bash
npm install
npm run dev:h5          # H5 本地预览（直连 wiidu；/seal-api 代理到 ../backend）
npm run dev:mp-weixin   # 微信小程序，开发者工具打开 dist/dev/mp-weixin
```

印章识别服务见上级目录 `../backend`。

## 推荐关系演示路径

1. 注册家长 A →「我的」复制推荐码  
2. 退出，注册家长 B 并填写 A 的码  
3. B 首页点「模拟开通会员」  
4. 切回 A，查看积分与「我的推荐」明细  
