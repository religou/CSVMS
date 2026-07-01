# Spec: 审计日志前后值展示优化

## Assumptions I'm Making

1. 本次范围聚焦审计日志列表页展示，不新增新的审计日志业务类型，也不重做审计日志查询接口。
2. “修改前”与“修改后”优先使用后端已经存在的 `old_value` 和 `new_value` 字段，而不是重新从业务表做 diff 计算。
3. 非更新类审计日志（如 `LOGIN`、`SIGN`）通常没有前后值，本次会在列表中显示 `-`，而不是人为拼装伪数据。
4. “去除 IP 列”指审计日志页面列表不再显示 IP，不要求删除数据库字段或修改签名等其他 API 的 IP 存储逻辑。
5. 当 `old_value` / `new_value` 内容较长时，UI 需要保证表格可读，不能因为原始值过长导致列表不可用。

## Objective

优化项目内审计日志页面，使审计记录更直接体现具体变更内容：

- 新增“修改前”列，展示审计记录的旧值。
- 新增“修改后”列，展示审计记录的新值。
- 去除当前的 “IP” 列。

用户故事：

- 作为项目成员，我需要在审计日志里直接看到修改前后的具体数据，而不是只知道改了哪个字段。
- 作为审计人员，我需要快速判断一次修改到底改了什么内容，而不必再回到原始业务对象推断。
- 作为系统使用者，我不需要在该页面优先关注 IP 信息，因此列表空间应优先留给真正的变更内容。

当前已知现状：

- [backend/app/models/audit_log.py](backend/app/models/audit_log.py#L30) 已经持久化 `old_value` 和 `new_value`。
- [backend/app/schemas/audit.py](backend/app/schemas/audit.py#L8) 已经把 `old_value`、`new_value`、`ip_address` 暴露给前端。
- [frontend/src/pages/AuditLog/index.tsx](frontend/src/pages/AuditLog/index.tsx#L60) 当前只显示时间、操作人、操作、资源类型、资源、变更字段、原因和 `IP`，没有展示前后值。

## Tech Stack

- Backend: Python 3.14, FastAPI, SQLAlchemy 2
- Frontend: React 18, TypeScript, Ant Design 5, Vite
- Testing: pytest（后端）, 前端当前以 `npm run build` 为主要验证手段

## Commands

- Frontend build: `Push-Location frontend; npm run build; Pop-Location`
- Frontend lint: `Push-Location frontend; npm run lint; Pop-Location`
- Backend focused tests: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_documents.py tests/test_signatures.py -v; Pop-Location`
- Backend full tests: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -v; Pop-Location`
- Frontend dev: `Push-Location frontend; npm run dev; Pop-Location`

## Project Structure

- `backend/app/models/audit_log.py` → 审计日志持久化字段定义
- `backend/app/schemas/audit.py` → 审计日志 API 响应契约
- `backend/app/services/audit_service.py` → 审计日志写入与查询服务
- `backend/app/api/v1/audit.py` → 审计日志查询接口
- `frontend/src/services/signatures.ts` → 审计日志前端类型与接口封装
- `frontend/src/pages/AuditLog/index.tsx` → 审计日志列表页面
- `backend/tests/test_documents.py` → 文档更新后审计日志回归测试
- `backend/tests/test_signatures.py` → 审计日志查询回归测试
- `docs/specs/audit-log-before-after-columns.md` → 本规格文档

## Code Style

本次变更优先保持现有 Ant Design `Table` 列定义风格，用显式列配置控制可读性：

```tsx
{
    title: '修改前',
    dataIndex: 'old_value',
    ellipsis: true,
    render: (value?: string) => value || '-',
}
```

约定：

- 列渲染优先展示真实原始值，不做二次翻译或业务推断。
- 长文本应使用现有表格可读模式，例如 `ellipsis`、固定宽度或带 tooltip 的截断，而不是无限撑开表格。
- 如果后端已有字段足够支撑需求，优先复用现有契约，不为了“展示优化”引入无必要的新接口或新表字段。

## Testing Strategy

- 后端优先验证现有审计日志测试仍通过，确保前后值字段没有被破坏。
- 如需补测试，应至少覆盖一条文档更新审计日志中 `old_value` / `new_value` 非空的场景。
- 前端至少执行 `npm run build`，确认审计日志页面表格列调整后类型和编译通过。
- 手工验证关键路径：打开项目内审计日志页，确认出现“修改前”“修改后”列，且 “IP” 列消失。

## Boundaries

- Always: 优先复用现有 `old_value` / `new_value` 字段；保持审计日志列表可读；对没有前后值的记录显示 `-`。
- Ask first: 是否需要把长文本展示改成交互式详情弹窗；是否要把 `IP` 从 API 契约里一并移除；是否要补充更多业务操作的前后值写入。
- Never: 为了前端展示去伪造不存在的前后值；删除已有审计日志数据；在未确认需求前修改签名或其他模块对 IP 的存储逻辑。

## Success Criteria

1. 审计日志页面新增“修改前”列，展示 `old_value` 的具体内容。
2. 审计日志页面新增“修改后”列，展示 `new_value` 的具体内容。
3. 审计日志页面移除当前的 “IP” 列。
4. 对没有前后值的审计记录，页面稳定显示 `-`，不出现空白或报错。
5. 长文本不会把审计日志表格撑坏，页面仍可正常浏览和分页。
6. 后端现有审计日志相关测试继续通过，前端构建通过。

## Open Questions

1. “修改前”“修改后”列对于超长文本，是否只需要截断展示，还是需要支持 hover 查看完整值？支持点击记录后，显示完整值
2. 是否只要求项目内审计日志页面变更，还是系统级其他复用审计日志数据的视图也要同步调整？同步调整，都需要有“修改前”和“修改后”列
