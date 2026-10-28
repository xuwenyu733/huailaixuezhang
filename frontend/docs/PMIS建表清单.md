# 淮来学长 · PMIS 建表清单

入口参考：[自定义表单](https://www.wiidu.com.cn/zx/customForm/customFormIndex1.html)  
操作规范见桌面：`pmis 使用守则/PMIS自定义数据表使用守则.md`

---

## 不可动范围

**只允许新建淮来学长相关表。禁止修改 / 删除 PMIS 里其它任何表或配置。**

1. 已有业务表（如 `test_table_learn_subjects` 等）一律不动  
2. 后台其它模块、已有自定义表单不动  
3. 服务端 JSP / 中间件不动  

---

## 已创建

| 内部表名 | 表备注 | 用途 | forminfo Id | 状态 |
|----------|--------|------|-------------|------|
| `test_table_hlxz_parent` | 淮来学长家长账号 | 家长登录注册 | 520 | ✅ |
| `test_table_hlxz_referral` | 淮来学长推荐关系 | 推荐绑定与积分 | 521 | ✅ |
| `test_table_hlxz_stamp` | 淮来学长盖章记录 | 虚拟/实体盖章 | 524 | ✅ |
| `test_table_hlxz_child` | 淮来学长孩子档案 | 家长绑定孩子 | 525 | ✅ |
| `test_table_hlxz_teacher` | 淮来学长教师账号 | 学校分配教师 | 526 | ✅ |
| `test_table_hlxz_goal` | 淮来学长激励目标 | 激励商城目标 | 527 | ✅ |
| `test_table_hlxz_order` | 淮来学长订单 | 会员/商品订单 | 528 | ✅ |
| `test_table_hlxz_message` | 淮来学长消息 | 站内消息 | 529 | ✅ |
| `test_table_hlxz_prefs` | 淮来学长偏好设置 | 通知/隐私开关 | 533 | ✅ |

系统自带隐藏字段：`Id` / `recId` / `isDel` / `createdTime` / `modifiedTime`（无需手建）。

代码表名常量：`src/constants/tables.ts`

### 盖章表主要字段 `test_table_hlxz_stamp`

owner_id / child_id / child_name / card_no / source(virtual|physical) / stamp_type / know_kind / stack_kind / subject / primary_dim / secondary_dim / code_* / value_* / teacher_* / image_url / note / status / created_at

### 孩子表主要字段 `test_table_hlxz_child`

parent_id / name / avatar_text / student_no / school / class_name / class_code / card_no / tag / is_current / created_at

### 教师表主要字段 `test_table_hlxz_teacher`

school_id / name / job_no / job_desc / stamp_no / phone / password / created_at

---

## 联调自测路径（本轮）

1. 手机号登录已有家长（如 15663306313）或新注册（自动 90 天试用）  
2. 我的 → 我的孩子 → 添加孩子（填记录卡编号）→ 长按设为当前  
3. 虚拟盖章 → 确认盖章（写入 stamp 表）  
4. 采集页 → 快门/相册 → 可改字段 → 确认上传（physical）  
5. 首页应看到最近记录与当量统计  
6. 商城 → 模拟开通会员 / 积分抵年费；我的推荐看真实列表  
7. 教师演示入口登录后 → 我的 → 教师管理 → 添加教师（印章编号唯一）  
