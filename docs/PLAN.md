# Implementation Plan: CSV 管理平台

## Phase 2: Technical Plan

### 实施策略

采用 MVP-First 方式，分 4 个里程碑递进交付：

```
M1: 基础架构 + 用户认证     →  能登录、能管理用户
M2: 文档管理 + 审批工作流   →  能创建文档、走审批流程
M3: 电子签名 + 审计追踪     →  合规核心能力
M4: 追溯矩阵 + 仪表板       →  完整 MVP
```

---

### 里程碑 1：基础架构 + 用户认证

**目标**：搭建前后端骨架，实现用户注册/登录/RBAC 权限管理。

**组件与依赖关系**：

```
数据库 Schema (users, roles, permissions)
    ↓
后端 Core (config, database, security)
    ↓
Auth API (login, register, token refresh)
    ↓
前端骨架 (路由, 布局, 登录页)
    ↓
Admin 页面 (用户管理, 角色分配)
```

**技术决策**：

- JWT 双 token 方案：access_token (15min) + refresh_token (7d)
- 密码策略：bcrypt 哈希，最小8位含大小写+数字+特殊字符
- RBAC：user → role → permission 三层模型
- 会话超时：30min 无操作前端自动登出
- 登录失败锁定：5次失败锁定15分钟

**风险**：
| 风险 | 缓解措施 |
|------|---------|
| 权限模型不够灵活 | 预留 permission 粒度到 resource_type × action |
| JWT 被盗用 | access_token 短有效期 + refresh_token 可主动撤销 |

---

### 里程碑 2：文档管理 + 审批工作流

**目标**：支持验证文档的全生命周期管理和可配置审批流程。

**组件与依赖关系**：

```
数据库 Schema (documents, doc_versions, workflows, workflow_steps)
    ↓
文档服务 (CRUD, 版本管理, 状态流转)
    ↓
工作流引擎 (流程配置, 步骤流转, 超时处理)
    ↓
文档 API + 工作流 API
    ↓
前端文档管理页 (列表, 编辑器, 版本对比)
    ↓
前端审批页面 (待办, 审批操作, 流程可视化)
```

**技术决策**：

- 文档版本：Copy-on-Write 模式，每次提交审核创建新版本快照
- 工作流引擎：状态机模式（不用 BPMN，复杂度不需要）
- 工作流配置：JSON Schema 定义流程模板
- 文档状态：`DRAFT → UNDER_REVIEW → APPROVED → EFFECTIVE → SUPERSEDED → RETIRED`
- 富文本编辑：TipTap (基于 ProseMirror)

**风险**：
| 风险 | 缓解措施 |
|------|---------|
| 工作流死锁（审批人离职） | 支持管理员强制流转 + 审批委托 |
| 文档内容冲突 | 单人编辑锁定，不支持协同编辑 |
| 大文档性能 | 内容分块存储，延迟加载 |

---

### 里程碑 3：电子签名 + 审计追踪

**目标**：实现 21 CFR Part 11 合规的电子签名和不可篡改的审计追踪。

**组件与依赖关系**：

```
签名服务 (身份验证, 签名生成, 哈希绑定)
    ↓
审计服务 (事件捕获, 只追加存储, 查询导出)
    ↓
签名 API + 审计 API
    ↓
签名弹窗组件 (身份重验, 含义声明)
    ↓
审计追踪页面 (查询, 过滤, 导出)
```

**技术决策**：

- 签名哈希：SHA-256(document_content + user_id + timestamp + meaning)
- 签名验证：每次签名必须重新输入 username + password（不使用已有 session）
- 审计记录：MySQL 表设置为 `INSERT ONLY`（应用层禁止 UPDATE/DELETE）
- 审计触发：SQLAlchemy event listener 自动捕获 ORM 变更
- 时间戳：服务器 UTC 时间，NTP 同步

**风险**：
| 风险 | 缓解措施 |
|------|---------|
| 审计表增长过快 | 按月分表 + 归档策略 |
| 签名哈希碰撞 | SHA-256 碰撞概率极低，足够合规 |
| 时间戳篡改 | NTP 强制同步，记录时区信息 |

---

### 里程碑 4：追溯矩阵 + 仪表板

**目标**：实现需求-设计-测试的全链路追溯和项目总览仪表板。

**组件与依赖关系**：

```
追溯关系模型 (traceability_links)
    ↓
追溯服务 (关联管理, 覆盖率计算, Gap 分析)
    ↓
报告服务 (统计聚合, 图表数据)
    ↓
追溯矩阵页面 (矩阵视图, 覆盖率展示)
    ↓
仪表板页面 (进度, 待办, 统计图)
```

**技术决策**：

- 追溯关系：document_id + requirement_item_id 多对多关联
- 覆盖率：实时计算，非物化视图（数据量可控）
- 仪表板数据：Redis 缓存聚合结果，5min TTL
- 图表：Ant Design Charts (基于 G2)

---

### 并行化分析

```
M1 完成后可以并行启动：
├── M2-后端（文档服务 + 工作流引擎）
├── M2-前端（文档管理页面骨架）  ← 可用 mock API 并行开发
└── M3-后端（审计追踪基础设施）  ← 与文档无直接依赖

M2 完成后：
├── M3-签名（依赖文档和工作流）
└── M4-追溯（依赖文档模型）
```

---

## Phase 3: Task Breakdown

### M1: 基础架构 + 用户认证

- [x] Task 1.1: 后端项目初始化
    - Acceptance: FastAPI 项目结构就绪，能 `uvicorn app.main:app --reload` 启动返回健康检查
    - Verify: `curl http://localhost:8000/health` 返回 200
    - Files: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/requirements.txt`

- [x] Task 1.2: 数据库模型 - 用户与权限
    - Acceptance: users, roles, permissions, user_roles 表创建成功
    - Verify: `alembic upgrade head` 无错误，表结构正确
    - Files: `backend/app/models/user.py`, `backend/alembic/`

- [x] Task 1.3: 用户认证 API
    - Acceptance: 注册、登录、token 刷新、密码策略验证全部可用
    - Verify: `pytest tests/test_auth.py` 全部通过
    - Files: `backend/app/api/v1/auth.py`, `backend/app/core/security.py`, `backend/app/schemas/auth.py`

- [x] Task 1.4: RBAC 权限中间件
    - Acceptance: API 路由基于角色权限控制访问
    - Verify: 无权限用户访问受限 API 返回 403
    - Files: `backend/app/api/deps.py`, `backend/app/services/permission_service.py`

- [x] Task 1.5: 用户管理 API
    - Acceptance: 管理员可 CRUD 用户、分配角色
    - Verify: `pytest tests/test_admin.py` 全部通过
    - Files: `backend/app/api/v1/admin.py`, `backend/app/services/user_service.py`

- [x] Task 1.6: 前端项目初始化
    - Acceptance: React + Vite + AntD + i18n 骨架就绪，能 `npm run dev` 启动
    - Verify: 浏览器访问 `http://localhost:5173` 显示页面
    - Files: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/main.tsx`, `frontend/src/App.tsx`

- [x] Task 1.7: 前端登录/注册页
    - Acceptance: 登录、注册表单可用，token 存储和自动刷新正常
    - Verify: 能登录并跳转到主页面
    - Files: `frontend/src/pages/Login/`, `frontend/src/services/auth.ts`, `frontend/src/stores/authStore.ts`

- [x] Task 1.8: 前端布局 + 路由 + 权限守卫
    - Acceptance: 侧边栏导航、面包屑、路由守卫（未登录跳转登录页）
    - Verify: 未登录访问任何页面重定向到 /login
    - Files: `frontend/src/components/Layout/`, `frontend/src/router/`, `frontend/src/hooks/useAuth.ts`

- [x] Task 1.9: 用户管理页面
    - Acceptance: 管理员可在界面上管理用户和角色
    - Verify: 创建用户 → 分配角色 → 验证权限生效
    - Files: `frontend/src/pages/Admin/`

---

### M2: 文档管理 + 审批工作流

- [x] Task 2.1: 数据库模型 - 文档与版本
    - Acceptance: documents, document_versions 表创建成功
    - Verify: 迁移无错误，支持 14 种文档类型枚举
    - Files: `backend/app/models/document.py`, `backend/alembic/`

- [x] Task 2.2: 文档 CRUD API
    - Acceptance: 创建、读取、更新、列表、按类型筛选全部可用
    - Verify: `pytest tests/test_documents.py` 全部通过
    - Files: `backend/app/api/v1/documents.py`, `backend/app/services/document_service.py`, `backend/app/schemas/document.py`

- [x] Task 2.3: 文档版本管理
    - Acceptance: 每次提交审核自动创建版本快照，支持版本列表和对比
    - Verify: 提交审核后 document_versions 新增记录
    - Files: `backend/app/services/document_service.py`

- [x] Task 2.4: 数据库模型 - 工作流
    - Acceptance: workflow_templates, workflows, workflow_steps 表创建成功
    - Verify: 迁移无错误
    - Files: `backend/app/models/workflow.py`, `backend/alembic/`

- [x] Task 2.5: 工作流引擎核心
    - Acceptance: 支持创建工作流实例、步骤流转（批准/退回/拒绝）、状态机约束
    - Verify: `pytest tests/test_workflow_engine.py` 覆盖所有流转路径
    - Files: `backend/app/services/workflow_service.py`

- [x] Task 2.6: 工作流 API
    - Acceptance: 提交审核、批准、退回、查看审批历史全部可用
    - Verify: `pytest tests/test_workflows.py` 全部通过
    - Files: `backend/app/api/v1/workflows.py`, `backend/app/schemas/workflow.py`

- [x] Task 2.7: 工作流模板配置
    - Acceptance: 管理员可配置不同文档类型的审批流程模板
    - Verify: 配置模板后新建文档自动关联对应流程
    - Files: `backend/app/api/v1/admin.py`, `backend/app/services/workflow_template_service.py`

- [x] Task 2.8: 前端文档管理页
    - Acceptance: 文档列表（筛选/搜索）、新建文档、文档详情页
    - Verify: 能创建各类型文档并查看
    - Files: `frontend/src/pages/Documents/`

- [x] Task 2.9: 前端文档编辑器
    - Acceptance: 富文本编辑（TipTap）、附件上传、自动保存
    - Verify: 编辑内容保存后刷新不丢失
    - Files: `frontend/src/components/DocumentEditor/`

- [x] Task 2.10: 前端审批工作流页面
    - Acceptance: 我的待办、审批操作（批准/退回）、审批历史、流程可视化
    - Verify: 完成一次完整的 起草→审核→批准 流程
    - Files: `frontend/src/pages/Workflows/`, `frontend/src/components/WorkflowStatus/`

---

### M3: 电子签名 + 审计追踪

- [x] Task 3.1: 数据库模型 - 签名与审计
    - Acceptance: signatures, audit_logs 表创建成功，audit_logs 表无 UPDATE/DELETE 触发器
    - Verify: 迁移无错误
    - Files: `backend/app/models/signature.py`, `backend/app/models/audit_log.py`, `backend/alembic/`

- [x] Task 3.2: 电子签名服务
    - Acceptance: 身份重验证、签名生成（含哈希）、签名验证、签名含义绑定
    - Verify: `pytest tests/test_signature.py` 覆盖正常/异常场景
    - Files: `backend/app/services/signature_service.py`, `backend/app/core/security.py`

- [x] Task 3.3: 电子签名 API
    - Acceptance: 签名提交、签名验证、签名记录查询
    - Verify: 错误密码签名失败，正确密码签名成功并记录
    - Files: `backend/app/api/v1/signatures.py`, `backend/app/schemas/signature.py`

- [x] Task 3.4: 审计追踪服务
    - Acceptance: SQLAlchemy event listener 自动记录所有 ORM 变更
    - Verify: 任何 CRUD 操作自动生成审计记录
    - Files: `backend/app/services/audit_service.py`, `backend/app/core/audit.py`

- [x] Task 3.5: 审计追踪 API
    - Acceptance: 查询（按时间/用户/资源筛选）、导出（CSV）
    - Verify: `pytest tests/test_audit.py` 全部通过
    - Files: `backend/app/api/v1/audit.py`, `backend/app/schemas/audit.py`

- [x] Task 3.6: 前端电子签名组件
    - Acceptance: 签名弹窗（用户名+密码+含义声明+备注）
    - Verify: 审批操作触发签名弹窗，签名后操作生效
    - Files: `frontend/src/components/SignatureModal/`

- [x] Task 3.7: 前端审计追踪页面
    - Acceptance: 审计日志查询、过滤、导出
    - Verify: 操作后审计页面即时显示记录
    - Files: `frontend/src/pages/AuditLog/`

- [x] Task 3.8: 签名与工作流集成
    - Acceptance: 审批操作（批准/退回）必须经过电子签名
    - Verify: 不签名无法完成审批操作
    - Files: `backend/app/services/workflow_service.py`, `frontend/src/pages/Workflows/`

---

### M4: 追溯矩阵 + 仪表板

- [x] Task 4.1: 数据库模型 - 追溯关系
    - Acceptance: traceability_links, requirement_items 表创建成功
    - Verify: 迁移无错误
    - Files: `backend/app/models/traceability.py`, `backend/alembic/`

- [x] Task 4.2: 追溯矩阵服务
    - Acceptance: 建立/删除关联、覆盖率计算、Gap 分析
    - Verify: `pytest tests/test_traceability.py` 全部通过
    - Files: `backend/app/services/traceability_service.py`

- [x] Task 4.3: 追溯矩阵 API
    - Acceptance: 关联 CRUD、覆盖率查询、矩阵数据查询
    - Verify: API 返回正确的追溯矩阵数据结构
    - Files: `backend/app/api/v1/traceability.py`, `backend/app/schemas/traceability.py`

- [x] Task 4.4: 仪表板 API
    - Acceptance: 项目进度、文档统计、待办汇总、审批耗时
    - Verify: 返回聚合数据正确
    - Files: `backend/app/api/v1/dashboard.py`

- [x] Task 4.5: 前端追溯矩阵页面
    - Acceptance: 矩阵视图、覆盖率展示、Gap 高亮
    - Verify: 能建立追溯关系并看到覆盖率变化
    - Files: `frontend/src/pages/Traceability/`

- [x] Task 4.6: 前端仪表板
    - Acceptance: 项目总览、待办事项、统计图表
    - Verify: 登录后首页展示仪表板数据
    - Files: `frontend/src/pages/Dashboard/`

- [x] Task 4.7: 国际化完善
    - Acceptance: 所有界面文本提取到 i18n 文件，中英文切换完整
    - Verify: 切换语言后所有文本正确显示
    - Files: `frontend/src/i18n/zh-CN.json`, `frontend/src/i18n/en-US.json`

---

## 验证检查点

每个里程碑结束时需通过以下检查：

| 检查项         | 方式                            |
| -------------- | ------------------------------- |
| 所有测试通过   | `pytest` + `npm run test`       |
| 无 lint 错误   | `ruff check` + `npm run lint`   |
| API 文档准确   | FastAPI 自动生成的 `/docs` 页面 |
| 可 Docker 构建 | `docker build` 无错误           |
| 手动验收       | 按 Task 的 Verify 步骤逐一确认  |

---

## 预估工作量

| 里程碑    | Tasks     | 说明                         |
| --------- | --------- | ---------------------------- |
| M1        | 9 个      | 基础架构，后续所有功能的地基 |
| M2        | 10 个     | 核心业务功能，工作量最大     |
| M3        | 8 个      | 合规关键模块                 |
| M4        | 7 个      | 增值功能                     |
| **Total** | **34 个** | —                            |

---

## 启动顺序

从 Task 1.1 开始，严格按依赖顺序执行。每完成一个 Task 立即验证后再进入下一个。
