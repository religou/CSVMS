# Spec: 权限管理文案调整

## Assumptions I'm Making

1. 本次只调整现有前端中文文案，不修改路由、权限码、接口契约或页面行为。
2. `/admin/roles` 仍然作为权限管理页面的路由，不会在这次变更中改路径。
3. “新建角色”改为“权限分配”仅针对页面主按钮文案；其现有点击行为保持不变，相关弹窗字段和创建流程暂不重构。

## Objective

将系统管理中的“角色权限”统一改名为“权限管理”，并将该页面顶部主按钮“新建角色”改为“权限分配”，让系统管理入口和页面名称更贴近当前业务表达。

## Tech Stack

- Frontend: React 18 + TypeScript + Ant Design 5 + React Router 6 + Vitest

## Commands

- Frontend targeted test: `Push-Location frontend; npm run test -- --run src/App.test.tsx; Pop-Location`
- Frontend build: `Push-Location frontend; npm run build; Pop-Location`

## Project Structure

- `frontend/src/components/Layout/AppLayout.tsx` → 系统管理左侧导航文案
- `frontend/src/pages/Admin/Roles.tsx` → 权限管理页面标题、按钮文案、提示文案
- `frontend/src/App.tsx` → 路由级 403 提示文案
- `frontend/src/App.test.tsx` → 路由守卫测试里的页面 mock 文案
- `docs/specs/permission-management-copy-update.md` → 本次文案调整 spec

## Code Style

```tsx
const adminChildren = [
    permissions.includes('system.admin.roles.menu')
        ? {
              key: '/admin/roles',
              label: '权限管理',
          }
        : null,
]
```

约定：

- 仅改用户可见文案，不借机调整无关逻辑。
- 同一语义的页面入口、页面标题和 403 提示使用一致命名。

## Testing Strategy

- 使用现有 Vitest 路由测试验证页面 mock 文案未破坏路由守卫测试。
- 使用 `npm run build` 验证改动未引入前端类型或打包回归。

## Boundaries

- Always: 保持路由、权限码、组件行为不变；同步更新测试中的相关展示文案。
- Ask first: 若需要把“权限分配”按钮行为也改成真正的权限分配流程，而不是只改文案。
- Never: 为了改文案修改 `/admin/roles` 路由或系统权限码。

## Success Criteria

1. 系统管理菜单中的“角色权限”显示为“权限管理”。
2. `/admin/roles` 页面标题中的“角色权限管理”显示为“权限管理”。
3. `/admin/roles` 页面顶部主按钮“新建角色”显示为“权限分配”。
4. 与该页面相关的无权限提示文案同步改为“权限管理页面访问权限”。
5. 前端目标测试和构建命令通过。

## Open Questions

- 无。当前按“仅改文案，不改行为”执行。
