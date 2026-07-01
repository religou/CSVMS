# Spec: 临床试验计算化系统验证（CSV）管理平台

## Objective

构建一个符合 GxP 法规要求的计算化系统验证（CSV）全生命周期管理平台，帮助制药/CRO企业高效管理临床试验相关计算化系统的验证过程。

### 核心价值

- **合规性**：满足 FDA 21 CFR Part 11、EU Annex 11、GAMP 5 要求
- **效率提升**：将纸质审批流程电子化，缩短验证周期
- **可追溯性**：完整审计追踪，支持监管检查

### 目标用户

| 角色       | 职责                         |
| ---------- | ---------------------------- |
| 验证专员   | 起草验证文档、执行测试脚本   |
| QA 人员    | 审核/批准文档，确保合规性    |
| IT 管理员  | 系统配置、用户管理、权限分配 |
| 项目经理   | 跟踪验证进度、资源分配       |
| 系统管理员 | 平台运维、审计追踪管理       |

### 成功标准

1. 支持完整的 CSV 生命周期管理（从 VMP 到退役）
2. 每个文档/过程具备可配置的多级审批工作流
3. 电子签名符合 21 CFR Part 11 要求（身份验证 + 签名含义 + 不可篡改 + 时间戳）
4. 完整审计追踪（who/what/when/why）
5. 支持 200+ 并发用户稳定运行
6. 中英文界面切换

---

## Tech Stack

| 层级     | 技术                                  | 版本                         |
| -------- | ------------------------------------- | ---------------------------- |
| 前端     | React + TypeScript                    | React 18+                    |
| UI 框架  | Ant Design                            | 5.x                          |
| 状态管理 | Zustand                               | 4.x                          |
| 后端     | Python + FastAPI                      | Python 3.11+, FastAPI 0.100+ |
| ORM      | SQLAlchemy                            | 2.x                          |
| 数据库   | MySQL                                 | 8.0+                         |
| 缓存     | Redis                                 | 7.x                          |
| 任务队列 | Celery + Redis                        | 5.x                          |
| 部署     | Docker（独立容器）                    | —                            |
| 认证     | JWT + RBAC                            | —                            |
| 国际化   | react-i18next (前端) / gettext (后端) | —                            |

---

## Commands

```bash
# 后端
cd backend
pip install -r requirements.txt          # 安装依赖
uvicorn app.main:app --reload            # 开发服务器
pytest --cov=app tests/                  # 运行测试
alembic upgrade head                     # 数据库迁移
alembic revision --autogenerate -m "msg" # 生成迁移

# 前端
cd frontend
npm install                              # 安装依赖
npm run dev                              # 开发服务器
npm run build                            # 生产构建
npm run test                             # 运行测试
npm run lint --fix                       # 代码检查

# Docker
docker build -t csvs-backend ./backend   # 构建后端镜像
docker build -t csvs-frontend ./frontend # 构建前端镜像
docker run -d -p 8000:8000 csvs-backend  # 启动后端
docker run -d -p 3000:80 csvs-frontend   # 启动前端
```

---

## Project Structure

```
CSVS/
├── docs/                        → 项目文档
│   ├── SPEC.md                  → 本规格说明
│   ├── api/                     → API 文档
│   └── adrs/                    → 架构决策记录
├── backend/
│   ├── app/
│   │   ├── main.py              → FastAPI 应用入口
│   │   ├── core/
│   │   │   ├── config.py        → 配置管理
│   │   │   ├── security.py      → 认证/授权/电子签名
│   │   │   ├── database.py      → 数据库连接
│   │   │   └── audit.py         → 审计追踪
│   │   ├── models/              → SQLAlchemy 数据模型
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   ├── document.py
│   │   │   ├── workflow.py
│   │   │   ├── signature.py
│   │   │   └── audit_log.py
│   │   ├── schemas/             → Pydantic 请求/响应模型
│   │   ├── api/                 → API 路由
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── workflows.py
│   │   │   │   ├── signatures.py
│   │   │   │   └── admin.py
│   │   │   └── deps.py          → 依赖注入
│   │   ├── services/            → 业务逻辑
│   │   │   ├── project_service.py
│   │   │   ├── document_service.py
│   │   │   ├── workflow_service.py
│   │   │   ├── signature_service.py
│   │   │   └── audit_service.py
│   │   └── utils/               → 工具函数
│   ├── alembic/                 → 数据库迁移
│   ├── tests/                   → 后端测试
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx             → 应用入口
│   │   ├── App.tsx
│   │   ├── components/          → 通用组件
│   │   │   ├── SignatureModal/  → 电子签名弹窗
│   │   │   ├── WorkflowStatus/ → 审批状态展示
│   │   │   ├── AuditTrail/     → 审计追踪展示
│   │   │   └── DocumentEditor/ → 文档编辑器
│   │   ├── pages/               → 页面
│   │   │   ├── Dashboard/
│   │   │   ├── Projects/
│   │   │   ├── Documents/
│   │   │   ├── Workflows/
│   │   │   ├── Admin/
│   │   │   └── AuditLog/
│   │   ├── stores/              → Zustand 状态
│   │   ├── services/            → API 调用
│   │   ├── hooks/               → 自定义 hooks
│   │   ├── i18n/                → 国际化
│   │   │   ├── zh-CN.json
│   │   │   └── en-US.json
│   │   ├── types/               → TypeScript 类型定义
│   │   └── utils/               → 工具函数
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
└── .github/                     → CI/CD & Skills
```

---

## 系统生命周期覆盖范围

平台管理以下 CSV 生命周期文档/过程，每个过程均支持审批工作流和电子签名：

| #   | 过程         | 缩写 | 说明                             |
| --- | ------------ | ---- | -------------------------------- |
| 1   | 验证主计划   | VMP  | 组织级别的验证策略和方针         |
| 2   | 验证计划     | VP   | 特定系统的验证范围和策略         |
| 3   | 用户需求规格 | URS  | 用户对系统的功能和非功能需求     |
| 4   | 功能规格     | FS   | 系统如何满足用户需求的功能描述   |
| 5   | 设计规格     | DS   | 系统技术设计和架构说明           |
| 6   | 安装确认     | IQ   | 确认系统按设计规格正确安装       |
| 7   | 运行确认     | OQ   | 确认系统在预期范围内正确运行     |
| 8   | 性能确认     | PQ   | 确认系统在实际使用条件下满足需求 |
| 9   | 追溯矩阵     | TM   | 需求-设计-测试的全链路追溯关系   |
| 10  | 验证总结报告 | VSR  | 验证活动的总结和结论             |
| 11  | 偏差管理     | DV   | 验证过程中偏差的记录和处理       |
| 12  | 变更控制     | CC   | 系统变更的评估、批准和实施       |
| 13  | 定期回顾     | PR   | 系统持续验证状态的定期评估       |
| 14  | 系统退役     | RET  | 系统停用的计划和执行             |

---

## 核心功能模块

### 1. 文档管理

```
功能：
- 文档创建（基于模板）
- 文档版本管理（主版本.次版本，如 1.0, 1.1, 2.0）
- 文档状态流转：草稿 → 审核中 → 已批准 → 已生效 → 已废止
- 文档关联（URS ↔ FS ↔ DS ↔ IQ/OQ/PQ）
- 文档模板管理
- 富文本编辑 + 附件上传
- PDF 导出（带电子签名水印）
```

### 2. 审批工作流引擎

```
功能：
- 可配置的审批流程（支持串行、并行、会签）
- 角色类型：起草人、审核人、批准人
- 流程动作：提交、批准、退回、拒绝、撤回
- 审批意见/批注
- 超时提醒和催办
- 审批委托（代理审批）
- 工作流模板（不同文档类型对应不同审批流）

流程示意：
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  起草   │───→│  审核   │───→│  批准   │───→│  生效   │
│ (Author)│    │(Reviewer)│   │(Approver)│   │(Effective)│
└─────────┘    └─────────┘    └─────────┘    └─────────┘
      ↑              │              │
      └──────────────┘──────────────┘
              退回 (Reject)
```

### 3. 电子签名（21 CFR Part 11）

```
合规要求：
- 签名由至少两个组件组成：用户 ID + 密码（或生物识别）
- 每次签名需重新验证身份（不可使用已登录 session）
- 签名含义声明（如"我审核了此文档"/"我批准了此文档"）
- 签名绑定到特定文档版本（不可迁移）
- 签名记录不可篡改（哈希校验）
- 精确时间戳（服务器时间，NTP 同步）
- 签名记录包含：签名人、时间、含义、文档标识、文档版本

数据模型：
{
  "signature_id": "uuid",
  "user_id": "签名人",
  "document_id": "文档ID",
  "document_version": "文档版本",
  "meaning": "审核/批准/起草",
  "timestamp": "2026-05-27T10:30:00Z",
  "hash": "sha256(document_content + user_id + timestamp)",
  "ip_address": "签名时IP",
  "is_valid": true
}
```

### 4. 审计追踪（Audit Trail）

```
记录范围：
- 所有数据的创建、修改、删除
- 用户登录/登出
- 文档状态变更
- 审批操作
- 电子签名操作
- 系统配置变更
- 权限变更

记录内容（WHO/WHAT/WHEN/WHY）：
{
  "audit_id": "uuid",
  "user_id": "操作人",
  "action": "UPDATE",
  "resource_type": "document",
  "resource_id": "文档ID",
  "field_changed": "content",
  "old_value": "修改前内容",
  "new_value": "修改后内容",
  "reason": "修改原因（必填）",
  "timestamp": "2026-05-27T10:30:00Z",
  "ip_address": "操作IP"
}

约束：
- 审计记录只可追加，不可修改/删除
- 管理员也无法删除审计记录
- 支持审计记录查询和导出
```

### 5. 用户与权限管理（RBAC）

```
权限模型：
- 用户 → 角色 → 权限
- 支持多角色分配
- 基于资源类型的权限粒度（文档类型 × 操作）
- 职责分离（起草人不能同时是批准人）

预设角色：
- 系统管理员(admin)：用户管理、系统配置
- 验证管理员(validation_admin)：模板管理、工作流配置
- 验证专员：起草文档、执行测试
- QA 审核员：审核文档
- QA 批准人：批准文档
- 只读用户：查看已生效文档

用户创建：
- 管理员（admin/validation_admin）可在管理后台新建用户
- 填写：用户名、邮箱、姓名、临时密码
- 角色可选（后续再分配）
- 不需要邮件通知，密码由管理员手动告知用户

菜单可见性规则：
- 顶层菜单：
  - admin / validation_admin 角色：项目列表 + 管理入口
  - 其他角色：仅项目列表入口
- 项目内菜单：所有成员均可见（概览/文档/审批/追溯/审计/成员）
- 操作按钮按项目角色控制：
  - viewer：无写操作按钮（新建文档、发起审批等不显示）
  - member/manager/owner：显示写操作按钮

admin 超级权限：
- admin 角色为系统超级用户，绕过所有项目成员权限限制
- 项目列表：显示系统中所有项目（不需要是成员）
- 进入项目：无需成员身份即可访问任何项目
- 项目内操作：拥有完全写权限（等同 owner）
- 成员管理：可管理任何项目的成员（添加/移除/改角色）
- 仅 admin 角色拥有此能力，validation_admin 不自动获得
```

### 6. 追溯矩阵

```
功能：
- 自动建立 URS → FS → DS → IQ/OQ/PQ 的追溯关系
- 覆盖率统计（每个需求是否有对应的测试用例）
- 正向追溯：需求 → 设计 → 测试
- 反向追溯：测试 → 设计 → 需求
- Gap 分析（未覆盖的需求/设计高亮显示）
- 可视化追溯矩阵导出
```

### 7. 仪表板与报告

```
功能：
- 验证项目进度总览
- 待办事项（我的待审批、我的草稿）
- 文档状态分布统计
- 审批耗时统计
- 偏差/变更趋势分析
- 自定义报告生成
```

### 8. 验证项目（Project）

```
概念：
- 一个"验证项目"对应一次验证活动（如某系统的 CSV 全流程）
- 项目是文档、工作流、追溯矩阵的顶层组织容器
- 不同项目之间数据完全隔离，项目成员才可访问项目内资源

数据模型：
- Project: id, name, code(唯一编号), system_name(被验证系统), description, status(active/completed/archived), created_by, created_at, updated_at
- ProjectMember: id, project_id, user_id, role(owner/manager/member/viewer), joined_at

权限模型：
- owner: 项目负责人，可管理成员、编辑项目、归档项目
- manager: 项目经理，可管理成员、编辑项目
- member: 普通成员，可创建/编辑文档、参与审批
- viewer: 只读查看

功能：
- 创建验证项目（自动成为 owner）
- 项目列表（仅显示当前用户参与的项目）
- 进入项目后展示项目内部导航（概览/文档/审批/追溯/审计/成员）
- 添加/移除项目成员，分配角色
- 文档归属项目（project_id），按项目过滤
- 追溯矩阵仅限项目内部文档之间建立
- 审计日志按项目过滤

导航流程：
  登录 → 项目列表 → 选择/进入项目 → 项目内页面
  └ 项目内：概览 | 文档管理 | 审批管理 | 追溯矩阵 | 审计日志 | 项目成员

约束（Out of Scope）：
- 不支持跨项目追溯
- 不支持跨项目文档共享
- 不支持项目模板
- 项目归档后为只读，不可创建新文档或发起新审批
```

---

## Code Style

### 后端 (Python/FastAPI)

```python
"""文档服务 - 管理验证文档的 CRUD 和状态流转."""

from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.core.audit import audit_log
from app.core.exceptions import BusinessError


class DocumentService:
    """验证文档服务."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @audit_log(action="CREATE", resource_type="document")
    async def create_document(
        self,
        data: DocumentCreate,
        author_id: UUID,
    ) -> Document:
        """创建新文档草稿."""
        document = Document(
            title=data.title,
            doc_type=data.doc_type,
            content=data.content,
            status=DocumentStatus.DRAFT,
            version="0.1",
            author_id=author_id,
            created_at=datetime.utcnow(),
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def submit_for_review(
        self,
        document_id: UUID,
        submitter_id: UUID,
    ) -> Document:
        """提交文档进入审核流程."""
        document = await self._get_document(document_id)
        if document.status != DocumentStatus.DRAFT:
            raise BusinessError("只有草稿状态的文档可以提交审核")
        if document.author_id != submitter_id:
            raise BusinessError("只有文档作者可以提交审核")

        document.status = DocumentStatus.UNDER_REVIEW
        await self.db.commit()
        return document
```

### 前端 (React/TypeScript)

```tsx
import { useState } from 'react'
import { Modal, Form, Input, message } from 'antd'
import { useTranslation } from 'react-i18next'
import { useSignDocument } from '@/hooks/useSignature'

interface SignatureModalProps {
    documentId: string
    meaning: 'review' | 'approve' | 'author'
    onSuccess: () => void
    onCancel: () => void
    open: boolean
}

/** 电子签名弹窗 - 符合 21 CFR Part 11 */
export function SignatureModal({
    documentId,
    meaning,
    onSuccess,
    onCancel,
    open,
}: SignatureModalProps) {
    const { t } = useTranslation()
    const [form] = Form.useForm()
    const { sign, loading } = useSignDocument()

    const handleSign = async () => {
        const values = await form.validateFields()
        await sign({
            documentId,
            meaning,
            userId: values.userId,
            password: values.password,
            comment: values.comment,
        })
        message.success(t('signature.success'))
        onSuccess()
    }

    return (
        <Modal
            title={t('signature.title')}
            open={open}
            onOk={handleSign}
            onCancel={onCancel}
            confirmLoading={loading}>
            <Form form={form} layout="vertical">
                <Form.Item
                    name="userId"
                    label={t('signature.userId')}
                    rules={[{ required: true }]}>
                    <Input />
                </Form.Item>
                <Form.Item
                    name="password"
                    label={t('signature.password')}
                    rules={[{ required: true }]}>
                    <Input.Password />
                </Form.Item>
                <Form.Item name="comment" label={t('signature.comment')}>
                    <Input.TextArea rows={3} />
                </Form.Item>
            </Form>
        </Modal>
    )
}
```

### 命名约定

| 元素             | 风格       | 示例                                   |
| ---------------- | ---------- | -------------------------------------- |
| Python 文件      | snake_case | `document_service.py`                  |
| Python 类        | PascalCase | `DocumentService`                      |
| Python 函数/变量 | snake_case | `create_document`                      |
| TS/React 组件    | PascalCase | `SignatureModal`                       |
| TS 文件（组件）  | PascalCase | `SignatureModal.tsx`                   |
| TS 文件（工具）  | camelCase  | `apiClient.ts`                         |
| API 路径         | kebab-case | `/api/v1/documents/{id}/submit-review` |
| 数据库表         | snake_case | `audit_logs`                           |

---

## Testing Strategy

| 层级         | 框架                           | 覆盖目标      | 位置                         |
| ------------ | ------------------------------ | ------------- | ---------------------------- |
| 后端单元测试 | pytest + pytest-asyncio        | ≥80%          | `backend/tests/unit/`        |
| 后端集成测试 | pytest + httpx                 | 关键 API 路径 | `backend/tests/integration/` |
| 前端单元测试 | Vitest + React Testing Library | ≥70%          | `frontend/src/**/__tests__/` |
| 前端 E2E     | Playwright                     | 关键用户流程  | `frontend/e2e/`              |

### 关键测试场景

1. **电子签名**
    - 密码错误时签名失败
    - 签名后文档哈希不可篡改
    - 签名时间戳精确性
    - 签名含义正确绑定

2. **审批工作流**
    - 正常流转：草稿 → 审核 → 批准
    - 退回后可重新提交
    - 职责分离：作者不可批准自己的文档
    - 并行会签全部通过才进入下一步

3. **审计追踪**
    - 所有 CRUD 操作生成审计记录
    - 审计记录不可删除
    - 记录包含完整的 WHO/WHAT/WHEN/WHY

4. **权限控制**
    - 未授权用户无法访问受限资源
    - 角色变更即时生效
    - 职责分离规则不可绕过

---

## Boundaries

### Always（始终遵守）

- 所有数据变更操作记录审计追踪
- 电子签名前必须重新验证用户身份
- 输入验证在 API 边界层（Pydantic schemas）
- 密码存储使用 bcrypt 哈希
- API 响应不暴露内部错误详情
- 数据库迁移通过 Alembic 管理，不手动修改表结构
- 每个 PR 必须包含对应的测试
- 敏感配置通过环境变量注入，不硬编码

### Ask First（需确认）

- 数据库 schema 变更
- 新增第三方依赖
- 修改审批工作流引擎核心逻辑
- 修改电子签名验证逻辑
- 修改权限模型
- 性能优化涉及架构变更

### Never（绝不）

- 不在代码中硬编码密码/密钥
- 不删除审计追踪记录
- 不绕过电子签名验证
- 不允许用户修改自己的审计记录
- 不在生产环境暴露调试接口
- 不使用 `--force` 推送到主分支
- 不删除数据库迁移文件

---

## Success Criteria

### MVP（最小可行产品）

- [ ] 用户注册/登录/权限管理
- [ ] 至少支持 URS、FS、IQ、OQ、PQ 五种文档类型
- [ ] 文档 CRUD + 版本管理
- [ ] 三级审批工作流（起草 → 审核 → 批准）
- [ ] 21 CFR Part 11 合规电子签名
- [ ] 完整审计追踪
- [ ] 追溯矩阵基础功能
- [ ] 中文界面

### V1.0（完整版）

- [ ] 全部 14 种文档/过程类型
- [ ] 可配置审批工作流（串行/并行/会签）
- [ ] 审批委托
- [ ] 文档模板管理
- [ ] 追溯矩阵可视化
- [ ] 偏差和变更控制流程
- [ ] 定期回顾提醒
- [ ] 仪表板和报告
- [ ] PDF 导出（带签名）
- [ ] 中英文切换
- [ ] 200+ 用户并发支持

---

## 数据模型（核心）

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    users     │     │  documents   │     │  signatures  │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id           │────→│ author_id    │     │ id           │
│ username     │     │ id           │←────│ document_id  │
│ email        │     │ title        │     │ user_id      │
│ password_hash│     │ doc_type     │     │ meaning      │
│ is_active    │     │ content      │     │ timestamp    │
│ created_at   │     │ status       │     │ hash         │
└──────────────┘     │ version      │     │ ip_address   │
                     │ created_at   │     └──────────────┘
                     │ updated_at   │
                     └──────────────┘
                            │
                            ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   workflows  │     │workflow_steps│     │  audit_logs  │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id           │────→│ workflow_id  │     │ id           │
│ document_id  │     │ step_order   │     │ user_id      │
│ template_id  │     │ role         │     │ action       │
│ status       │     │ assignee_id  │     │ resource_type│
│ created_at   │     │ status       │     │ resource_id  │
└──────────────┘     │ comment      │     │ old_value    │
                     │ signed_at    │     │ new_value    │
                     └──────────────┘     │ reason       │
                                          │ timestamp    │
                                          │ ip_address   │
                                          └──────────────┘
```

---

## 非功能需求

| 指标     | 目标                            |
| -------- | ------------------------------- |
| 响应时间 | API P95 < 500ms                 |
| 并发用户 | ≥200 同时在线                   |
| 可用性   | 99.5% uptime                    |
| 数据备份 | 每日全量 + 实时 binlog          |
| 密码策略 | 最小8位，含大小写+数字+特殊字符 |
| 会话超时 | 30分钟无操作自动登出            |
| 登录失败 | 5次失败锁定15分钟               |

---

## Open Questions

1. ~~技术栈选择~~ → 已确认：React + Python/FastAPI + MySQL
2. ~~部署方式~~ → 已确认：Docker 独立容器
3. 是否需要支持文档协同编辑（多人同时编辑同一文档）？需要
4. 电子签名是否需要支持 USB Key / CA 证书等硬件签名方式？不需要
5. 是否需要支持离线签名（断网后补签）？不需要
6. 文档附件大小限制？不限制
7. 数据保留策略（审计记录保留多少年）？10 年
8. 是否需要支持多租户（多个组织共用一个平台实例）？不需要
