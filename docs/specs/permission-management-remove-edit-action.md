# Spec: 权限管理操作列移除编辑按钮

## Assumptions I'm Making

1. 本次变更目标页面是 `/admin/roles`，即当前“权限管理”页面，而不是其他带“操作”列的管理页面。
2. 用户诉求是移除列表“操作”列中的“编辑”按钮，不涉及新增替代入口。
3. 当“编辑”入口被移除后，页面内所有“仍可编辑展示信息”的提示文案也应同步调整，避免出现与实际 UI 不一致的说明。
4. 本次不修改后端接口、权限码、路由或数据库，只处理前端展示与相关前端测试。

## Objective

在权限管理页面中移除角色列表“操作”列里的“编辑”按钮，收缩该页可见操作，仅保留与权限分配和删除相关的入口；同时校正文案，确保页面不再暗示当前列表仍支持角色编辑。

## Tech Stack

- Frontend: React 18 + TypeScript + Ant Design 5 + React Router 6 + Vitest

## Commands

- Frontend targeted test: `Push-Location frontend; npm run test -- --run src/pages/Admin/Roles.test.tsx; Pop-Location`
- Frontend build: `Push-Location frontend; npm run build; Pop-Location`

## Project Structure

- `frontend/src/pages/Admin/Roles.tsx` -> 权限管理页面表格操作列、提示文案、可能的编辑入口状态
- `frontend/src/pages/Admin/Roles.test.tsx` -> 权限管理页面行为测试
- `docs/specs/permission-management-remove-edit-action.md` -> 本次变更规格

## Code Style

```tsx
const columns = [
    {
        title: '操作',
        key: 'actions',
        render: (_: unknown, record: RoleDetailItem) => (
            <Space>
                <Button
                    size="small"
                    icon={<SafetyCertificateOutlined />}
                    onClick={() => openPermissionsModal(record)}>
                    权限
                </Button>
                <Button size="small" danger>
                    删除
                </Button>
            </Space>
        ),
    },
]
```

约定：

- 只移除与本需求直接相关的 UI 入口和失真的提示文案，不借机调整权限规则。
- 如某段状态、处理函数或弹窗在移除按钮后变成纯死代码，应在实现计划阶段明确是同步删除还是保留待后续处理。

## Testing Strategy

- 使用 Vitest 更新或补充角色页测试，验证“编辑”按钮不再出现在权限管理列表的操作列中。
- 验证“权限”“删除”等保留操作仍按现有权限约束显示/禁用。
- 运行前端打包命令，确认改动未引入类型错误或构建回归。

## Boundaries

- Always: 仅调整权限管理页面前端展示；保持现有接口契约、权限校验和路由不变；同步修正与“可编辑”能力冲突的页面提示文案。
- Ask first: 若要彻底删除“编辑角色”弹窗、相关状态和提交逻辑，而不是仅移除入口按钮。
- Never: 为了移除按钮修改后端角色编辑接口、权限码定义、数据库结构或其他管理页面的操作列。

## Success Criteria

1. 权限管理页面角色列表“操作”列不再渲染“编辑”按钮。
2. 用户在该页面不能再通过列表直接打开“编辑角色”入口。
3. 页面上所有与该入口直接相关、且会误导用户认为仍可从此处编辑角色的提示文案被同步修正。
4. “权限”和“删除”操作保持现有行为与权限约束不变。
5. `Push-Location frontend; npm run test -- --run src/pages/Admin/Roles.test.tsx; Pop-Location` 通过。
6. `Push-Location frontend; npm run build; Pop-Location` 通过。

## Open Questions

- 无。

## Plan

1. 先在角色页测试中补一个行为断言，明确角色列表的“操作”列不再出现“编辑”按钮，并保持“权限分配”等现有入口不受影响。
2. 在 `frontend/src/pages/Admin/Roles.tsx` 中移除列表操作列的“编辑”按钮，仅保留“权限”“删除”操作。
3. 同步修正页面内会误导用户认为仍可从此处编辑角色的提示文案，但不删除现有编辑弹窗逻辑与状态，以符合方案 1。
4. 运行角色页目标测试与前端构建，确认该 UI 收缩未引入回归。

风险与缓解：

- 风险：页面提示文案仍残留“可编辑展示信息”，与 UI 不一致。
  缓解：集中检查 `Roles.tsx` 内与管理权限有关的 Tooltip、Alert 和空状态文案，并在测试后再做一次构建验证。
- 风险：测试通过但构建因未使用导入或类型收窄变化失败。
  缓解：在移除按钮后运行 `npm run build`，让 TypeScript 捕获未使用符号或 JSX 变更问题。

验证检查点：

- 检查点 1：新增测试先失败，证明当前页面仍渲染“编辑”按钮。
- 检查点 2：最小实现后，角色页目标测试通过。
- 检查点 3：前端构建通过，确认无类型或打包回归。

## Tasks

- [x] Task: 补充角色页回归测试，覆盖“操作”列不显示编辑按钮
    - Acceptance: 角色页测试能稳定断言列表中不存在“编辑”按钮，且“权限分配”按钮仍存在
    - Verify: `Push-Location frontend; npm run test -- --run src/pages/Admin/Roles.test.tsx; Pop-Location`
    - Files: `frontend/src/pages/Admin/Roles.test.tsx`

- [x] Task: 移除权限管理列表中的编辑按钮并修正相关提示文案
    - Acceptance: 角色列表操作列仅保留“权限”“删除”，相关提示不再声明当前页可编辑展示信息
    - Verify: `Push-Location frontend; npm run test -- --run src/pages/Admin/Roles.test.tsx; Pop-Location`
    - Files: `frontend/src/pages/Admin/Roles.tsx`

- [x] Task: 执行前端构建验证
    - Acceptance: 前端构建成功
    - Verify: `Push-Location frontend; npm run build; Pop-Location`
    - Files: 无代码改动

## Decision Log

- 已确认按方案 1 执行：仅移除权限管理列表中的“编辑”按钮并修正文案，保留现有编辑弹窗与相关状态，不在本次改动中继续清理无入口流程。
