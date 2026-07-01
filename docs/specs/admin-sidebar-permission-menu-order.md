# Spec: 系统管理侧边栏权限管理菜单顺序调整

## Assumptions I'm Making

1. 本次变更仅针对系统管理左侧导航子菜单的显示顺序，不涉及项目侧菜单。
2. “移动到字典管理菜单的下面”表示在系统管理分组中将顺序调整为“用户管理 -> 字典管理 -> 权限管理”。
3. 本次不修改任一路由、权限码、菜单文案或菜单可见性判断，只调整已显示菜单项的排列顺序。
4. 当前菜单顺序的唯一控制点是 `frontend/src/components/Layout/AppLayout.tsx` 中的 `adminChildren` 数组。

如果这些假设不对，需要在进入实现前修订本 spec。

## Objective

调整系统管理左侧导航中“权限管理”菜单项的位置，使其显示在“字典管理”菜单项之后，让系统管理分组中的菜单顺序更符合当前期望的业务排列。

## Tech Stack

- Frontend: React 18 + TypeScript + Ant Design 5 + React Router 6 + Vitest

## Commands

- Frontend targeted test: `Push-Location frontend; npm run test -- --run src/components/Layout/AppLayout.test.tsx; Pop-Location`
- Frontend build: `Push-Location frontend; npm run build; Pop-Location`
- Frontend dev: `Push-Location frontend; npm run dev; Pop-Location`

## Project Structure

- `frontend/src/components/Layout/AppLayout.tsx` -> 系统管理左侧导航菜单定义与排序控制点
- `frontend/src/components/Layout/AppLayout.test.tsx` -> 侧边栏菜单顺序回归测试（若本次补充）
- `docs/specs/admin-sidebar-permission-menu-order.md` -> 本次菜单排序调整规格

## Code Style

```tsx
const adminChildren = [
    permissions.includes('system.admin.users.menu')
        ? { key: '/admin/users', label: '用户管理' }
        : null,
    permissions.includes('system.admin.dict.menu')
        ? { key: '/admin/dict', label: '字典管理' }
        : null,
    permissions.includes('system.admin.roles.menu')
        ? { key: '/admin/roles', label: '权限管理' }
        : null,
].filter((item): item is NonNullable<typeof item> => item !== null)
```

约定：

- 优先通过最小重排解决问题，不借机抽象菜单配置或重构布局组件。
- 菜单排序应直接体现在声明顺序中，避免引入额外排序逻辑影响现有权限过滤。

## Testing Strategy

- 如果补充前端测试，优先覆盖 `AppLayout` 在同时具备系统管理菜单权限时的子菜单显示顺序。
- 至少运行前端构建，确认菜单顺序调整未引入类型或打包错误。
- 手工验证时，使用拥有 `system.admin.users.menu`、`system.admin.dict.menu`、`system.admin.roles.menu` 的账号确认展开“系统管理”后顺序为“用户管理 -> 字典管理 -> 权限管理”。

## Boundaries

- Always: 保持现有菜单权限过滤逻辑、路由 key、图标和文案不变；只调整系统管理子菜单顺序。
- Ask first: 如果希望顺带统一重排其他系统管理菜单，或把菜单顺序提取为可配置常量。
- Never: 为了调整显示顺序修改权限码、页面访问控制、路由跳转逻辑或其他非系统管理菜单结构。

## Success Criteria

1. 在拥有相关菜单权限的情况下，系统管理左侧子菜单顺序显示为“用户管理 -> 字典管理 -> 权限管理”。
2. “权限管理”菜单仍指向 `/admin/roles`，“字典管理”菜单仍指向 `/admin/dict`，其他菜单项行为不变。
3. 各菜单项的权限控制逻辑保持不变，只是显示顺序发生调整。
4. `Push-Location frontend; npm run build; Pop-Location` 通过。
5. 若补充了菜单顺序测试，则对应前端测试通过。

## Open Questions

- 无。当前按“仅调整系统管理子菜单显示顺序”执行。

## Plan

1. 先补一个针对 `AppLayout` 的前端回归测试，明确当系统管理三个菜单都可见时，显示顺序必须是“用户管理 -> 字典管理 -> 权限管理”。
2. 在 `frontend/src/components/Layout/AppLayout.tsx` 中仅调整 `adminChildren` 的声明顺序，把“权限管理”移动到“字典管理”之后。
3. 运行新增的目标测试和前端构建，确认本次变更只影响显示顺序，不引入类型或打包回归。

风险与缓解：

- 风险：Ant Design `Menu` 的渲染结构导致顺序测试不稳定。
  缓解：测试直接比较三个菜单项所在 DOM 节点的先后顺序，而不是依赖快照或整段文本匹配。
- 风险：菜单顺序被改动后误触发其他布局逻辑回归。
  缓解：保持实现只改 `adminChildren` 的数组顺序，并用构建验证类型与打包结果。

验证检查点：

- 检查点 1：新增菜单顺序测试先失败，证明当前顺序与目标不一致。
- 检查点 2：调整顺序后，目标测试通过。
- 检查点 3：前端构建通过。

## Tasks

- [x] Task: 补充系统管理菜单顺序回归测试
    - Acceptance: 在同时具备系统管理三个菜单权限时，测试可明确断言顺序为“用户管理 -> 字典管理 -> 权限管理”
    - Verify: `Push-Location frontend; npm run test -- --run src/components/Layout/AppLayout.test.tsx; Pop-Location`
    - Files: `frontend/src/components/Layout/AppLayout.test.tsx`

- [x] Task: 调整系统管理子菜单中权限管理的位置
    - Acceptance: `adminChildren` 中“权限管理”位于“字典管理”之后，其他菜单项行为不变
    - Verify: `Push-Location frontend; npm run test -- --run src/components/Layout/AppLayout.test.tsx; Pop-Location`
    - Files: `frontend/src/components/Layout/AppLayout.tsx`

- [x] Task: 执行前端构建验证
    - Acceptance: 前端构建成功
    - Verify: `Push-Location frontend; npm run build; Pop-Location`
    - Files: 无代码改动
