# Spec: 权限分配角色来源对齐

## Assumptions I'm Making

1. 本次只改“权限管理”页里的“权限分配”入口流程，不同时重构整个权限管理页列表结构。
2. 点击“权限分配”后，不再要求手输新的角色编码，而是从“字典管理”中的 `system_role` 和 `project_role` 现有字典项中选择目标角色。
3. “选完角色之后，可以直接配置权限”指同一条交互流程内完成“选择角色 + 展示当前权限 + 修改并保存”，而不是跳转到第二个页面。
4. 系统角色权限仍然持久化在 `roles` / `role_permissions` 上；权限分配弹窗只是把可选角色来源改成 `system_role` 字典项，并按 `code == roles.name` 做映射。
5. 如果某个 `system_role` 字典项在 `roles` 表里没有同名角色，本次先按“不可直接配置并提示同步缺失”处理，而不是自动创建新 `roles` 记录。
6. 项目角色权限继续持久化在 `dict_items.permission_profile` 与 `dict_items.permission_codes` 上，不会并入 `roles` 表。
7. 当前用户管理、登录鉴权、项目成员权限生效逻辑保持不变；本次聚焦权限分配入口和对应保存路径。

如果以上假设有误，尤其是第 4 和第 5 条，需要先纠正，我再进入 Plan。

## Objective

将“权限管理”页中的“权限分配”从“新建一个角色编码再配置权限”的流程，改成“从字典管理里已有的系统角色或项目角色中选择角色，然后直接配置权限”的流程，避免重复造角色编码，并让权限配置入口与字典中的角色定义保持一致。

### 用户故事

- 作为管理员，我点击“权限分配”时，应该先看到已有角色列表，而不是输入一个新的角色编码。
- 作为管理员，我可以从“系统角色”或“项目角色”中选定目标角色，并立刻看到它当前的权限配置。
- 作为管理员，我修改完系统角色或项目角色的权限后，可以直接保存，不需要再回到字典管理或新建角色页面。

## Tech Stack

- Frontend: React 18 + TypeScript + Ant Design 5 + Zustand + React Router 6 + Vitest
- Backend: FastAPI + SQLAlchemy 2 + Pydantic v2
- Existing persistence split:
    - System roles: `roles` / `role_permissions`
    - Project roles: `dict_categories(code='project_role')` + `dict_items.permission_profile` / `permission_codes`

## Commands

- Frontend targeted tests: `Push-Location frontend; npm run test -- --run src/App.test.tsx src/pages/Admin/DictManagement.test.tsx; Pop-Location`
- Frontend build: `Push-Location frontend; npm run build; Pop-Location`
- Backend focused tests if API changes: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_admin.py tests/test_dictionary.py -v; Pop-Location`

## Project Structure

- `frontend/src/pages/Admin/Roles.tsx` → 当前“权限管理”页，现状仍把“权限分配”实现成新建角色流程
- `frontend/src/pages/Admin/DictManagement.tsx` → 当前字典管理页，已维护 `system_role` 与 `project_role`
- `frontend/src/services/admin.ts` → 系统角色和权限 API 封装
- `frontend/src/services/dictionary.ts` → 字典与项目角色权限配置 API 封装
- `backend/app/api/v1/admin.py` → 系统角色权限分配接口
- `backend/app/api/v1/dictionary.py` → 项目角色权限配置接口
- `backend/app/schemas/dictionary.py` → `project_role.permission_codes` 契约
- `docs/specs/permission-assignment-role-source-alignment.md` → 本规格文档

## Code Style

```tsx
type AssignableRoleOption = {
    sourceType: 'system_role' | 'project_role'
    code: string
    label: string
    description?: string
}

const groupedRoleOptions = [
    {
        label: '系统角色',
        options: systemRoleItems.map((item) => ({
            value: `system_role:${item.code}`,
            label: item.label,
        })),
    },
    {
        label: '项目角色',
        options: projectRoleItems.map((item) => ({
            value: `project_role:${item.code}`,
            label: item.label,
        })),
    },
]
```

约定：

- “权限分配”入口不再出现自由输入角色编码的字段。
- 系统角色和项目角色在 UI 上明确区分来源，但在同一条操作流里完成选择与配置。
- 保存时必须根据角色来源走对应持久化路径，而不是强行共用一套提交结构。

## Testing Strategy

- Frontend Vitest 覆盖：
    - 点击“权限分配”时，弹窗提供分组后的“系统角色 / 项目角色”选择项。
    - 选择系统角色后，加载对应 `roles` 实体的当前权限并允许保存。
    - 选择项目角色后，加载对应 `permission_profile` / `permission_codes` 并允许保存。
    - `system_role` 字典项缺少对应 `roles` 记录时，出现明确提示，不允许误保存。
- Frontend 额外执行 `npm run build`。
- 如果实现中需要新增后端辅助接口或同步校验，再补 `test_admin.py` / `test_dictionary.py` focused regression。

## Boundaries

- Always: “权限分配”角色来源必须来自字典管理中的现有角色；系统角色和项目角色要在同一入口可选；选完角色后要能直接看到并修改当前权限配置。
- Ask first: 是否要把整个权限管理页主表也改成同时展示系统角色和项目角色；是否要在权限分配时自动补齐缺失的 `roles` 记录。
- Never: 在“权限分配”流程里继续要求输入新的角色编码；把项目角色错误地保存进 `roles` 表；为了兼容 UI 直接绕过现有权限持久化路径。

## Success Criteria

1. 点击“权限分配”后，不再出现“角色编码”自由输入框。
2. 弹窗中可选择的角色来源于字典管理中的 `system_role` 和 `project_role`，并按来源分组展示。
3. 选择系统角色后，可直接加载并保存该系统角色的权限配置。
4. 选择项目角色后，可直接加载并保存该项目角色的 `permission_profile` 与 `permission_codes` 配置。
5. 如果所选系统角色在 `roles` 表中不存在对应记录，界面会给出明确提示，而不是悄悄新建角色编码。
6. 现有用户分配角色、登录态权限读取、项目权限生效逻辑不因本次入口调整而回退。

## Resolved Decisions

1. 当 `system_role` 字典项与 `roles` 表不一致时，本次按“提示缺失并禁止保存”处理，不自动补齐 `roles` 记录。
2. 本次范围只覆盖“权限分配”入口流程，不同时重构“权限管理”页主表，也不把项目角色并入当前主表展示。

## Implementation Plan

### Overview

本次实现采用“前端交互重构优先、尽量复用现有后端接口”的方案。目标不是重做整页权限管理，而是把当前“权限分配 = 新建系统角色”的错误交互，改成“从字典角色中选目标角色，再按角色来源直接编辑权限”。如果现有接口已足够支撑，就不新增后端接口；只有在保存路径或缺失校验无法由现有接口表达时，才补最小后端改动。

### Major Components

1. **角色来源聚合层**
   在权限管理页同时读取三类数据：
    - `system_role` 字典项
    - `project_role` 字典项
    - `roles` / `permissions` 现有系统角色与权限目录

    其中系统角色需要建立“字典项 code -> roles.name”的映射；项目角色直接使用字典项自身的 `permission_profile` / `permission_codes`。

2. **权限分配弹窗重构**
   把当前“角色编码 + 显示名称 + 说明”的新建角色表单改成：
    - 角色来源选择：`系统角色` / `项目角色`
    - 目标角色选择：来自对应字典类别
    - 当前权限展示与编辑：按来源过滤出 `system.*` 或 `project.*` 权限
    - 项目角色额外展示当前 `permission_profile`

3. **分流保存路径**
    - 系统角色：根据选中的字典项 code 查找 `roles` 实体，找到后调用现有系统角色权限更新接口；找不到则前端直接阻止保存并提示“请先同步系统角色数据”。
    - 项目角色：调用现有字典项更新接口，直接保存 `permission_codes`，并保留已有 `permission_profile`。

4. **错误与边界处理**
    - `system_role` 字典有、`roles` 无对应项时，禁用保存并给出清晰错误提示。
    - 切换角色来源时，清空上一个来源的已选角色和权限状态，避免脏数据串用。
    - 保持当前主表的编辑/删除系统角色逻辑不变，不把本次权限分配改动扩散到无关列表交互。

### Implementation Order

1. **先梳理前端数据模型**
   在权限管理页接入字典角色数据，并构建统一的可选角色结构与映射关系。

2. **再替换权限分配弹窗交互**
   去掉自由输入角色编码，改为来源选择 + 角色选择 + 权限选择。

3. **接入保存分流与缺失校验**
   让系统角色和项目角色分别走现有正确持久化路径，并落下“缺失 `roles` 记录禁止保存”的交互保护。

4. **最后补回归测试与构建验证**
   优先覆盖权限分配入口的角色来源、缺失提示和保存路径分流。

### Risks and Mitigations

| Risk                                                                          | Impact | Mitigation                                                                             |
| ----------------------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------- |
| `system_role` 字典与 `roles` 表不一致导致系统角色无法配置                     | High   | 明确在 UI 上提示缺失并禁用保存，把问题暴露给管理员而不是隐式创建脏数据                 |
| 同一弹窗同时承载系统角色和项目角色，状态容易串用                              | Medium | 角色来源切换时重置选中角色、已选权限和错误提示；保存前按来源重新校验                   |
| 现有 `permissions` 目录同时包含 `system.*` 和 `project.*`，弹窗容易展示错范围 | Medium | 按角色来源严格过滤权限选项，只显示对应前缀的权限码                                     |
| 项目角色权限编辑与字典管理页形成两处入口，逻辑可能不一致                      | Medium | 权限管理页复用字典接口与同样的 `permission_codes` 字段，不引入第二套项目角色持久化模型 |

### Parallelization Opportunities

- 这次改动主要集中在 `frontend/src/pages/Admin/Roles.tsx`，核心实现基本串行。
- 若需要补最小后端校验或辅助查询，可与前端测试编写并行，但前提是前端交互契约先固定。

### Checkpoints

#### Checkpoint A: 角色来源聚合完成后

- [ ] 权限管理页可以同时拿到 `system_role`、`project_role` 和 `roles`/`permissions` 数据
- [ ] 系统角色字典项与 `roles` 实体的映射规则明确且可判定缺失

#### Checkpoint B: 权限分配弹窗替换后

- [ ] 不再出现自由输入“角色编码”字段
- [ ] 可以按来源选择系统角色或项目角色
- [ ] 角色切换时当前权限显示和编辑区域同步切换

#### Checkpoint C: 保存路径分流完成后

- [ ] 系统角色权限更新走 `roles` / `role_permissions`
- [ ] 项目角色权限更新走 `dict_items.permission_codes`
- [ ] 缺失 `roles` 记录时会明确阻止保存

#### Checkpoint D: 回归验证完成后

- [ ] Frontend targeted tests 通过
- [ ] Frontend build 通过
- [ ] 若有后端改动，focused backend tests 通过

## Open Questions

- 当前无阻塞实现的未决问题；若后续希望把权限管理主表扩展成同时展示系统角色和项目角色，另开下一轮 scope。
