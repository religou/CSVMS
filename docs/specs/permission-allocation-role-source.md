# Spec: 权限分配角色来源调整

## Assumptions I'm Making

1. 本次改动聚焦“权限管理”页面里的“权限分配”交互，不改变现有用户分配系统角色、项目成员分配项目角色的主流程。
2. 点击“权限分配”后，不应再让管理员手工输入新的角色编码，而是必须从“字典管理”里的“系统角色”或“项目角色”中选择已有角色。
3. 系统角色的权限持久化仍然落在后端 `roles` / `role_permissions` 上；前端从 `system_role` 字典选择角色后，后端按相同角色编码映射到 `roles.name`。
4. 项目角色的权限持久化仍然落在 `dict_items.permission_codes` 上；前端从 `project_role` 字典选择角色后，直接编辑该字典项的权限集合。
5. 系统角色与项目角色在“权限分配”里使用同一套权限目录，但保存时按角色类型分别过滤：系统角色仅配置 `system.*`，项目角色仅配置 `project.*`。
6. 如果某个“系统角色”字典项没有对应的 `roles` 记录，本次先按“阻止保存并给出明确错误”处理，而不是隐式自动创建 `roles` 记录。

如果以上假设不对，尤其是第 6 条，需要在进入 Plan 阶段前纠正。

## Objective

把“权限管理”页面里的“权限分配”从“新建一个系统角色”改成“选择一个来自字典管理的已有角色并直接配置权限”。管理员点击“权限分配”后，应先选择角色类型（系统角色 / 项目角色），再从对应字典类别中选择角色，然后在同一个流程里直接查看并调整该角色当前权限。

### User Stories

- 作为系统管理员，我点击“权限分配”时，不需要再手工输入角色编码，而是可以直接从“系统角色”或“项目角色”里选择一个已有角色。
- 作为系统管理员，我选中某个系统角色后，可以直接配置它的系统菜单、页面和按钮权限。
- 作为系统管理员，我选中某个项目角色后，可以直接配置它的项目菜单、页面和按钮权限。
- 作为系统管理员，如果选中的系统角色在后端没有对应可持久化的系统角色实体，我会得到明确错误，而不是看到一个看似成功但实际无效的保存结果。

## Tech Stack

- Frontend: React 18 + TypeScript + Ant Design 5 + Zustand + React Router 6 + Vitest
- Backend: FastAPI + SQLAlchemy 2 + Pydantic
- Database: MySQL runtime / SQLite test

## Commands

- Frontend targeted tests: `Push-Location frontend; npm run test -- --run src/App.test.tsx src/pages/Admin/DictManagement.test.tsx; Pop-Location`
- Frontend build: `Push-Location frontend; npm run build; Pop-Location`
- Backend focused tests: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_admin.py tests/test_dictionary.py -v; Pop-Location`
- Backend full tests: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -v; Pop-Location`

## Project Structure

- `frontend/src/pages/Admin/Roles.tsx` → 当前权限管理页面，现状是“权限分配”仍走新建角色表单
- `frontend/src/services/admin.ts` → 系统角色与权限目录 API 封装
- `frontend/src/services/dictionary.ts` → 字典类别/字典项 API 封装，已承载 `project_role.permission_codes`
- `frontend/src/pages/Admin/DictManagement.tsx` → 当前项目角色权限编辑页，可作为项目角色权限配置逻辑参考
- `backend/app/api/v1/admin.py` → 系统角色权限读取、更新、删除接口
- `backend/app/api/v1/dictionary.py` → 项目角色字典读取与 `permission_codes` 更新接口
- `backend/app/schemas/dictionary.py` → 项目角色权限映射契约
- `docs/specs/permission-allocation-role-source.md` → 本次权限分配角色来源变更 spec

## Code Style

```tsx
const roleSourceOptions = [
    { value: 'system_role', label: '系统角色' },
    { value: 'project_role', label: '项目角色' },
]

const permissionOptions = allPermissions.filter((permission) =>
    selectedRoleType === 'system_role'
        ? permission.code.startsWith('system.')
        : permission.code.startsWith('project.'),
)
```

约定：

- UI 上的“角色选择”优先展示字典管理中的角色来源，而不是让用户输入自由文本角色编码。
- 系统角色与项目角色共用交互壳，但保存路径必须显式分流，不能混写到同一个接口。
- 若系统角色字典项缺少对应 `roles` 实体，必须返回清晰错误，不做隐式数据修补。

## Testing Strategy

- 前端用 Vitest 覆盖：点击“权限分配”时不再出现角色编码输入框；切换系统角色/项目角色后，角色选项来源正确；选中角色后能加载并提交对应权限。
- 后端用 pytest 覆盖：系统角色按字典编码映射 `roles` 实体更新权限；项目角色更新 `permission_codes`；系统角色缺少对应 `roles` 记录时返回明确错误。
- 最低验证包括前端 targeted tests、前端 build，以及后端 focused tests。

## Boundaries

- Always: 角色来源必须是字典管理中的“系统角色”或“项目角色”；系统角色和项目角色的权限保存路径必须分离；已有权限码体系保持不变。
- Ask first: 是否允许在“权限管理”页面里顺带创建新的字典角色；是否要在保存系统角色权限时自动补建缺失的 `roles` 实体。
- Never: 再次要求管理员在“权限分配”弹窗里手工输入新的角色编码；把项目角色权限写进 `roles` 表；把系统角色权限直接写回 `system_role` 字典项。

## Success Criteria

1. 点击“权限分配”后，界面先要求选择角色类型和已有角色，不再出现“角色编码”手工输入框。
2. “系统角色”下拉选项来源于字典管理中的 `system_role` 类别；“项目角色”下拉选项来源于字典管理中的 `project_role` 类别。
3. 选中系统角色后，可直接查看和保存该角色的系统权限；保存时更新对应 `roles` / `role_permissions`。
4. 选中项目角色后，可直接查看和保存该角色的项目权限；保存时更新对应 `dict_items.permission_codes`。
5. 若所选系统角色字典项没有对应 `roles` 实体，保存会明确失败并提示管理员，而不是静默成功。
6. 前端 targeted tests、前端 build、后端 focused tests 通过。

## Open Questions

1. 若 `system_role` 字典里新增了一个角色，但还没有对应 `roles` 表记录，是否应在权限分配保存时自动创建该系统角色，还是维持本 spec 第 6 条假设，直接报错并要求先补齐数据？
