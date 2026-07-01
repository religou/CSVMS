# CSVMS - 计算化系统验证管理平台

CSVMS（Computerized System Validation Management System）是一个面向制药/CRO 企业的计算化系统验证（CSV）全生命周期管理平台，帮助团队以电子化方式管理验证文档、审批流程、电子签名与审计追踪，满足 FDA 21 CFR Part 11、EU Annex 11、GAMP 5 等法规要求。

## 核心价值

- **合规性**：符合 21 CFR Part 11 电子签名要求、完整不可篡改的审计追踪
- **效率提升**：将纸质审批流程电子化，支持可配置的多级审批工作流
- **可追溯性**：需求—设计—测试的全链路追溯矩阵，支持覆盖率与 Gap 分析
- **多语言**：中英文界面切换

## 功能模块

- **用户与权限管理（RBAC）**：用户/角色/权限三层模型，支持项目级成员角色（owner/manager/member/viewer）
- **验证项目管理**：以项目为容器组织文档、工作流、追溯矩阵，项目间数据隔离
- **文档管理**：覆盖 VMP、VP、URS、FS、DS、IQ、OQ、PQ、TM、VSR 等 14 种 CSV 生命周期文档类型，支持版本管理与状态流转（草稿→审核中→已批准→已生效→已废止）
- **审批工作流引擎**：可配置的多级审批流程（起草→审核→批准），支持批准/退回/拒绝
- **电子签名**：符合 21 CFR Part 11 的身份重验证 + 签名含义声明 + 哈希绑定
- **审计追踪**：自动记录所有数据变更（WHO/WHAT/WHEN/WHY），审计记录只可追加、不可篡改
- **追溯矩阵**：需求与设计、测试之间的关联关系管理及覆盖率统计
- **仪表板**：项目进度、待办事项、文档状态统计等总览信息

## 技术栈

| 层级     | 技术                       |
| -------- | -------------------------- |
| 前端     | React 18 + TypeScript      |
| UI 框架  | Ant Design 5               |
| 状态管理 | Zustand                    |
| 构建工具 | Vite                       |
| 国际化   | react-i18next              |
| 后端     | Python + FastAPI           |
| ORM      | SQLAlchemy 2（异步）       |
| 数据库   | MySQL 8.0+                 |
| 缓存/队列 | Redis + Celery            |
| 认证     | JWT + RBAC                 |
| 数据库迁移 | Alembic                  |

## 项目结构

```
CSVMS/
├── backend/          → FastAPI 后端服务
│   ├── app/
│   │   ├── main.py       → 应用入口
│   │   ├── core/         → 配置、数据库、安全、异常
│   │   ├── models/       → SQLAlchemy 数据模型
│   │   ├── schemas/      → Pydantic 请求/响应模型
│   │   ├── api/v1/       → API 路由
│   │   ├── services/     → 业务逻辑
│   │   └── scripts/      → 初始化/种子数据脚本
│   ├── alembic/       → 数据库迁移
│   └── tests/         → 后端测试（pytest）
├── frontend/          → React 前端应用
│   └── src/
│       ├── pages/        → 页面（Dashboard/Projects/Documents/Workflows/Admin/AuditLog 等）
│       ├── components/   → 通用组件
│       ├── stores/       → Zustand 状态
│       ├── services/     → API 调用
│       ├── hooks/        → 自定义 hooks
│       └── i18n/         → 国际化文案
├── docs/              → 项目文档（规格、实施计划、专项说明）
└── deploy/            → 部署与本地运行指南
```

## 快速开始

### 前置要求

- Python 3.12+
- Node.js 18+
- MySQL 8.0+
- Redis（可选，用于缓存与任务队列）

### 后端

```powershell
cd backend
pip install -r requirements.txt
copy .env.example .env   # 并根据实际情况修改数据库等配置
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 前端

```powershell
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 即可使用（开发环境已配置 `/api` 请求代理到后端 8000 端口）。

更多本地环境搭建细节（数据库建库、账号配置等）请参考 [`deploy/local.md`](deploy/local.md)。

## 常用命令

```bash
# 后端
cd backend
pytest --cov=app tests/                   # 运行测试
alembic revision --autogenerate -m "msg"  # 生成新的数据库迁移

# 前端
cd frontend
npm run build     # 生产构建
npm run test      # 运行测试
npm run lint      # 代码检查
```

## 文档

- [`docs/SPEC.md`](docs/SPEC.md) — 产品与技术规格说明
- [`docs/PLAN.md`](docs/PLAN.md) — 实施计划与里程碑
- [`docs/specs/`](docs/specs/) — 各功能专项设计说明
- [`deploy/local.md`](deploy/local.md) — 本地运行指南

## 安全提示

- 生产环境务必修改 `.env` 中的 `SECRET_KEY`、数据库密码等默认值
- 审计记录仅支持追加写入，任何角色（包括管理员）均不可修改或删除
