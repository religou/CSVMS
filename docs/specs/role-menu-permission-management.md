# Spec: 系统角色与菜单权限管理

## Assumptions I'm Making

1. 本次范围是现有 Web 前后端，不包含移动端、第三方组织架构同步、SSO 或外部 IAM 集成。
2. “菜单权限管理”在本阶段指对现有系统菜单和项目菜单的可见性与页面访问权限进行配置，不包含拖拽式动态菜单设计器或任意新菜单树编辑。
3. 系统角色仍然是“分配给用户的全局角色”，项目角色仍然是“分配给项目成员关系的项目内角色”，两者不会合并为同一张业务表。
4. 项目角色继续保留现有 `permission_profile`（`owner` / `manager` / `member` / `viewer`）作为业务动作权限档位；菜单和按钮权限配置不能破坏这套既有动作权限语义。
5. 首期至少覆盖当前已存在的系统菜单与项目菜单：系统侧包括“用户管理”“字典管理”；项目侧包括“概览”“文档管理”“审批管理”“追溯矩阵”“审计日志”“项目成员”。
6. 当前登录态只返回角色，不返回权限；本次需求允许扩展认证响应或新增权限查询接口，用于前端渲染菜单、页面和按钮权限。
7. 现有 `system_role` 与 `project_role` 字典数据需要保留兼容，不能因为引入菜单权限配置而让当前用户分配、项目成员角色或项目权限判断失效。

如果以上假设有误，需要在进入 Tasks 阶段前修订 spec。

## Objective

在系统管理中新增统一的“角色 & 菜单权限管理”能力，让管理员可以配置系统角色和项目内角色所拥有的菜单、页面和按钮访问权限，并让前后端都基于配置结果控制可见性与访问，而不是继续依赖硬编码判断。

### 用户故事

- 作为系统管理员，我可以在系统管理中查看和维护系统角色，并为每个系统角色分配可访问的系统菜单与按钮权限。
- 作为系统管理员，我可以配置项目角色的展示信息、权限档位和可访问的项目菜单与按钮，而不需要修改代码。
- 作为普通用户，我登录后只会看到自己有权访问的系统菜单，并且无法操作无权限的按钮。
- 作为项目成员，我进入项目后只会看到自己当前项目角色允许访问的项目菜单和项目内操作入口。
- 作为开发人员，我希望权限来源统一且可追踪，避免前端写死角色名、后端又维护另一套权限规则。

### 当前已知现状

- [backend/app/models/user.py](backend/app/models/user.py#L74) 已有 `Role`、`Permission` 以及 `role_permissions` 关系模型，说明系统级 RBAC 基础数据结构已经存在。
- [backend/app/api/v1/admin.py](backend/app/api/v1/admin.py#L235) 当前只提供角色列表、创建角色和权限列表接口，缺少角色更新、删除、分配权限等完整管理能力。
- [frontend/src/pages/Admin/index.tsx](frontend/src/pages/Admin/index.tsx#L42) 当前用户管理页选择系统角色时仍直接读取 `system_role` 字典，而不是读取真正可管理的系统角色实体。
- [frontend/src/components/Layout/AppLayout.tsx](frontend/src/components/Layout/AppLayout.tsx#L21) 当前系统菜单是否显示是通过 `admin` / `validation_admin` 的硬编码角色名判断。
- [frontend/src/components/Layout/ProjectLayout.tsx](frontend/src/components/Layout/ProjectLayout.tsx#L27) 当前项目菜单是固定数组，对项目角色没有任何菜单级权限控制。
- [frontend/src/pages/Admin/DictManagement.tsx](frontend/src/pages/Admin/DictManagement.tsx#L22) 当前项目角色通过 `project_role` 字典维护，并已支持 `permission_profile`，但还不支持项目菜单或按钮权限配置。

## Tech Stack

- Backend: Python 3.14, FastAPI, SQLAlchemy 2, Alembic
- Frontend: React 18, TypeScript, Ant Design 5, Zustand, Vite
- Database: MySQL（运行环境） / SQLite + aiosqlite（测试环境）
- Auth: JWT access/refresh token + `/auth/me`

## Commands

- Backend focused tests: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_admin.py tests/test_projects.py -v; Pop-Location`
- Backend full tests: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -v; Pop-Location`
- Backend migrations: `Push-Location backend; alembic upgrade head; Pop-Location`
- Frontend build: `Push-Location frontend; npm run build; Pop-Location`
- Frontend dev: `Push-Location frontend; npm run dev; Pop-Location`
- Backend dev: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir c:/Users/zhouek/Work/SelfProject/CSVS/backend`

## Project Structure

- `backend/app/models/user.py` → 系统用户、系统角色、系统权限模型
- `backend/app/api/v1/admin.py` → 系统管理接口，当前已有用户管理、部分角色/权限读取能力
- `backend/app/api/v1/auth.py` → 登录与当前用户信息响应，后续需要扩展权限载荷
- `backend/app/api/deps.py` → `require_roles` / `require_permissions` 权限检查入口
- `backend/app/models/dictionary.py` → 字典类别与字典项模型，当前承载 `project_role`
- `backend/app/services/project_service.py` → 项目成员角色和项目业务动作权限逻辑
- `frontend/src/pages/Admin/index.tsx` → 当前系统管理中的用户管理页
- `frontend/src/pages/Admin/DictManagement.tsx` → 当前字典管理页，已用于维护 `project_role`
- `frontend/src/components/Layout/AppLayout.tsx` → 系统级菜单渲染，当前角色名硬编码
- `frontend/src/components/Layout/ProjectLayout.tsx` → 项目级菜单渲染，当前固定菜单无权限过滤
- `frontend/src/services/admin.ts` → 管理端前端 API 封装
- `frontend/src/services/auth.ts` → 当前用户信息前端契约
- `frontend/src/stores/authStore.ts` → 登录态状态存储
- `backend/tests/test_admin.py` → 系统管理/角色分配回归测试
- `backend/tests/test_projects.py` → 项目角色与项目权限回归测试
- `docs/specs/role-menu-permission-management.md` → 本规格文档

## Code Style

本次能力优先沿用“后端以稳定权限码判断，前端以权限集合过滤菜单/页面/按钮”的风格，不继续在页面里硬编码角色名：

```ts
const visibleSystemMenus = SYSTEM_MENU_ITEMS.filter((item) =>
    currentUser.permissions.includes(item.permission_code),
)
```

```python
@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(
    role_id: str,
    data: RolePermissionUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    role = await service.update_role_permissions(role_id, data.permission_codes)
    return RoleResponse.model_validate(role)
```

约定：

- 权限判断优先依赖稳定的权限码，不依赖页面字符串或硬编码角色名。
- 系统菜单权限与项目菜单权限应使用明确、可枚举的权限定义，不在前端自由拼接魔法字符串。
- 项目角色的业务动作权限继续由 `permission_profile` 决定；菜单、页面和按钮权限是额外配置层，不替代已有业务动作判断。
- 新增权限相关接口继续保持“路由薄层 + service 业务封装”的现有项目风格。

## Testing Strategy

- 后端使用 pytest，重点覆盖：系统角色权限分配、角色更新/删除限制、项目角色菜单/按钮权限配置、权限查询响应、无权限访问的拒绝路径。
- 后端至少要有一条回归测试证明：系统菜单显示权限不再只依赖 `admin` / `validation_admin` 角色名，而是依赖角色关联的权限配置。
- 后端至少要有一条回归测试证明：项目角色权限配置变化后，项目内有效权限查询结果能反映到菜单和按钮权限集合。
- 前端至少执行 `npm run build`；如果增加前端自动化测试，优先覆盖 `AppLayout` 与 `ProjectLayout` 的菜单过滤、按钮禁用和路由守卫逻辑。
- 手工验证关键路径：
    - 以管理员身份配置系统角色权限后，目标用户重新登录可见菜单发生变化。
    - 以不同项目角色进入同一项目时，左侧项目菜单和关键按钮按配置收敛。
    - 直接访问无权限路由或触发无权限操作时会被拦截，而不是仅仅隐藏菜单。

## Boundaries

- Always: 菜单权限必须同时控制“菜单可见性”“路由/页面访问”和“页面内按钮级操作”；后端必须保留最终权限校验；现有 `permission_profile` 语义必须保持兼容；内置角色和内置菜单的初始权限映射必须可种子化/可迁移。
- Ask first: 是否允许管理员自定义新增菜单节点；是否把字段级/数据级权限一并纳入这次权限管理；是否需要把项目按钮权限抽成比菜单权限更细的独立配置层。
- Never: 继续在布局组件中硬编码角色名决定菜单；只做前端隐藏而不做后端访问控制；在系统角色和项目角色上各维护一套互不一致的菜单定义；为了兼容旧逻辑而绕过权限校验。

## Success Criteria

1. 系统管理中存在明确的角色权限管理入口，管理员可以查看并维护系统角色的菜单与按钮权限配置。
2. 管理员可以配置项目角色的展示信息、`permission_profile`，以及基于默认模板可微调的项目菜单与按钮权限配置。
3. 用户管理分配系统角色时，前端和后端都以 `roles` 实体作为唯一来源，不再依赖 `system_role` 字典作为角色分配来源。
4. 登录后的用户信息或权限查询结果中，包含渲染系统菜单和系统按钮所需的权限数据，前端不再通过 `admin` / `validation_admin` 等硬编码角色名决定可见性。
5. 项目详情或项目权限接口中包含当前用户在当前项目下的有效权限数据，项目菜单与按钮都按该结果进行过滤。
6. 即使用户手工输入无权限路由或直接触发无权限操作，也会被前端守卫或后端权限校验明确拒绝，而不是绕过权限限制。
7. `admin` 角色支持编辑、权限分配和删除；`validation_admin` 只允许编辑显示信息，不允许做权限分配，并按受限内置角色处理。
8. 现有系统内置角色、现有项目角色以及当前项目动作权限行为保持兼容，不因菜单权限管理上线而破坏用户管理、项目成员管理、文档管理等既有流程。
9. 相关后端回归测试通过，前端至少完成构建验证；如果补充前端测试，新增菜单/按钮过滤场景也必须通过。

## Resolved Decisions

1. 系统角色以 `roles` 表为唯一来源；`system_role` 字典不再作为系统角色分配和展示的业务来源。
2. `admin` 作为可管理内置角色，允许在管理界面删除，也允许编辑显示信息和权限分配。
3. `validation_admin` 作为受限内置角色，只允许编辑角色展示信息；不参与权限分配，也不作为可删除角色处理。
4. 菜单权限范围同时覆盖左侧导航、页面访问和页面内按钮级操作权限。
5. 项目角色权限配置采用“按 `permission_profile` 自动带出默认菜单/按钮权限，再允许管理员微调”的模式。

## Implementation Plan

### Overview

本次实现按“先统一权限契约，再分系统角色和项目角色两条线接入，最后切前端菜单/页面/按钮控制”的顺序推进。目标不是仅仅把菜单隐藏规则从硬编码改到配置，而是建立一套可以同时服务系统角色、项目角色、导航可见性、页面访问和按钮操作的统一权限来源。

### Architecture Decisions

1. **权限目录继续以 `permissions` 表为中心。**
   系统菜单、系统页面、系统按钮、项目菜单、项目页面和项目按钮都定义为显式权限码，避免前端拼字符串或继续依赖角色名硬编码。现有 `Role.permissions` 与 `require_permissions` 直接复用。

2. **系统角色完全收敛到 `roles` + `role_permissions`。**
   用户管理中的系统角色选择、角色列表与权限分配都以 `roles` 表为准，不再读取 `system_role` 字典；`system_role` 字典仅作为历史兼容数据处理对象，最终退出该职责。

3. **项目角色继续使用 `project_role` 字典，但新增独立的权限映射层。**
   `permission_profile` 继续负责项目内业务动作语义；菜单、页面和按钮权限采用新的映射关系保存，而不是复用 `extra` 或篡改 `permission_profile` 含义。这样展示信息、动作档位和权限配置三者保持分离。

4. **前端权限状态拆成“系统权限”和“项目上下文权限”两层。**
   登录态或 `/auth/me` 返回系统权限集合，用于系统菜单、系统页面和系统按钮控制；进入项目后，再加载当前用户在该项目下的有效权限集合，用于项目菜单、项目页面和项目按钮控制。

5. **按钮权限与菜单权限共用同一套权限码体系。**
   例如“查看用户管理页”和“编辑用户”应是不同权限码，但都属于统一目录，前端通过同一套权限判断工具控制菜单、路由和按钮，不再散落 `isAdmin`、`myPermissionProfile === 'owner'` 之类的局部判断。

6. **项目业务动作后端校验继续保留 `permission_profile` 兜底。**
   即使前端按钮已隐藏，`ProjectService` 这类服务层仍然保留现有 owner/manager/member/viewer 语义校验，确保 UI 权限与业务权限双重一致，而不是只靠前端拦截。

### Implementation Order

1. **权限基础层与迁移层先落地。**
   定义首批系统/项目权限码，补种子数据与迁移；新增项目角色与权限的映射表；把内置系统角色和内置项目角色的默认权限关系写入初始化或迁移逻辑。

2. **先完成系统角色后端能力。**
   扩展角色管理 API，补齐系统角色列表、更新、删除、权限分配和受限内置角色约束；同时把用户管理页的角色来源从 `system_role` 字典切到 `roles` 实体。

3. **再完成项目角色后端能力。**
   为 `project_role` 维护页面增加菜单、页面和按钮权限配置契约，并实现“按 `permission_profile` 生成默认权限 + 人工微调保存”的后端逻辑；提供当前项目有效权限查询能力。

4. **再扩展认证与权限查询契约。**
   在 `/auth/me` 或专用权限接口中返回系统权限；在项目上下文增加当前用户有效项目权限查询接口，保证前端不需要自行推导权限。

5. **最后接前端管理界面和权限控制。**
   新增系统角色权限管理界面，更新用户管理的角色来源；在系统布局、项目布局、路由守卫和关键页面按钮中统一接入权限判断工具，替换当前硬编码逻辑。

### Risks and Mitigations

| Risk                                                                         | Impact | Mitigation                                                             |
| ---------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------- |
| 系统角色从 `system_role` 字典切到 `roles` 后，现有用户分配与登录展示可能断裂 | High   | 先做角色数据迁移/回填，再切前后端读取路径；在切换期间保留后端兼容解析  |
| 页面内按钮权限覆盖范围广，容易出现漏控或规则不一致                           | High   | 定义统一权限常量与通用判断 Hook/工具，先覆盖核心页面，再按任务切片扩展 |
| 项目角色既有 `permission_profile` 又要新增菜单/按钮权限映射，容易混淆职责    | Medium | 数据模型上显式分离“动作档位”和“权限映射”；保存与查询接口分别命名       |
| 内置角色的特殊约束容易只做前端限制，导致后端可绕过                           | Medium | 受限角色规则全部由后端强制校验，前端只做禁用态展示                     |
| 系统权限与项目权限都需要前端状态缓存，切项目时可能出现脏数据                 | Medium | 系统权限和项目权限分开存储，进入/切换项目时显式重新拉取项目权限集合    |

### Parallelization Opportunities

- 在权限码契约和接口字段冻结后，“系统角色后端 API” 与 “系统角色前端管理界面” 可以并行推进。
- 在项目角色权限映射契约冻结后，“项目角色后端映射逻辑” 与 “项目布局/按钮前端权限接入” 可以并行推进。
- 数据迁移、认证响应契约修改和权限常量定义必须先完成，属于串行依赖。

### Checkpoints

#### Checkpoint A: 权限基础层完成后

- [ ] 权限码目录、迁移和默认映射已确定
- [ ] 内置系统角色和内置项目角色的默认权限回填可执行
- [ ] 相关后端基础测试通过

#### Checkpoint B: 系统角色链路完成后

- [ ] 系统角色 CRUD / 权限分配能力可用
- [ ] 用户管理角色来源已切到 `roles` 实体
- [ ] `/auth/me` 或等价接口可返回系统权限
- [ ] `backend/tests/test_admin.py` 相关回归通过

#### Checkpoint C: 项目角色链路完成后

- [ ] 项目角色支持默认权限生成与手动微调
- [ ] 当前项目有效权限查询可用
- [ ] 现有 `permission_profile` 业务动作权限未回退
- [ ] `backend/tests/test_projects.py` 相关回归通过

#### Checkpoint D: 前端权限接入完成后

- [ ] 系统菜单、项目菜单、关键页面按钮均按权限控制
- [ ] 无权限路由被明确拦截
- [ ] 前端构建通过，关键路径手工验证通过

## Task Breakdown

- [ ] Task: 定义权限目录与默认种子
    - Acceptance: 系统菜单、系统页面、系统按钮、项目菜单、项目页面、项目按钮都有稳定权限码定义；内置系统角色默认权限和项目角色默认权限模板可初始化到数据库。
    - Verify: `Push-Location backend; alembic upgrade head; Pop-Location`
    - Verify: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_admin.py -k "permission or role" -v; Pop-Location`
    - Files: `backend/alembic/versions/*`, `backend/app/models/user.py`, `backend/app/scripts/*`, `backend/tests/test_admin.py`

- [ ] Task: 落地项目角色权限映射持久层
    - Acceptance: `project_role` 能保存菜单、页面和按钮权限映射；权限配置与 `permission_profile` 分离；缺失映射时可基于 `permission_profile` 生成默认模板。
    - Verify: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_projects.py -k "permission" -v; Pop-Location`
    - Files: `backend/app/models/dictionary.py`, `backend/app/schemas/dictionary.py`, `backend/app/api/v1/dictionary.py`, `backend/alembic/versions/*`, `backend/tests/test_projects.py`

- [ ] Task: 补齐系统角色管理后端接口
    - Acceptance: 系统角色支持列表、更新、删除、权限分配；`admin` 可删除且可分配权限；`validation_admin` 只能编辑展示信息，不能删除或分配权限。
    - Verify: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_admin.py -k "role" -v; Pop-Location`
    - Files: `backend/app/api/v1/admin.py`, `backend/app/schemas/user.py`, `backend/tests/test_admin.py`, `backend/app/services/*`

- [ ] Task: 切换系统角色分配来源到 roles 实体
    - Acceptance: 用户创建、用户分配角色、角色列表展示都只依赖 `roles` 表；`system_role` 字典不再参与系统角色分配流程。
    - Verify: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_admin.py -v; Pop-Location`
    - Files: `backend/app/api/v1/admin.py`, `frontend/src/services/admin.ts`, `frontend/src/pages/Admin/index.tsx`, `backend/tests/test_admin.py`

- [ ] Task: 扩展系统权限查询契约
    - Acceptance: 登录态或 `/auth/me` 能返回系统权限集合；前端状态层可持有系统权限，不再只保存角色名。
    - Verify: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_auth.py tests/test_admin.py -v; Pop-Location`
    - Verify: `Push-Location frontend; npm run build; Pop-Location`
    - Files: `backend/app/api/v1/auth.py`, `backend/app/schemas/auth.py`, `frontend/src/services/auth.ts`, `frontend/src/stores/authStore.ts`, `backend/tests/test_auth.py`

- [ ] Task: 实现系统角色权限管理界面
    - Acceptance: 系统管理中存在角色权限管理入口；管理员可查看角色、编辑角色展示信息、配置权限、删除允许删除的内置角色或普通角色；受限角色有明确禁用态和提示。
    - Verify: `Push-Location frontend; npm run build; Pop-Location`
    - Files: `frontend/src/pages/Admin/index.tsx`, `frontend/src/services/admin.ts`, `frontend/src/App.tsx`, `frontend/src/pages/Admin/*`

- [ ] Task: 扩展项目权限查询与项目角色管理 UI
    - Acceptance: 项目上下文接口返回当前用户有效项目权限；字典管理中的 `project_role` 可配置默认模板和微调后的菜单、页面、按钮权限。
    - Verify: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/test_projects.py -v; Pop-Location`
    - Verify: `Push-Location frontend; npm run build; Pop-Location`
    - Files: `backend/app/api/v1/projects.py`, `backend/app/schemas/project.py`, `backend/tests/test_projects.py`, `frontend/src/pages/Admin/DictManagement.tsx`, `frontend/src/services/dictionary.ts`

- [ ] Task: 替换系统与项目端的权限硬编码
    - Acceptance: `AppLayout`、`ProjectLayout` 和关键页面按钮都基于权限集合判断显示/禁用；无权限路由被明确拦截；原有 `isAdmin`、硬编码角色名和局部项目角色判断从菜单/按钮控制路径移除。
    - Verify: `Push-Location frontend; npm run build; Pop-Location`
    - Verify: 手工验证系统菜单、项目菜单、关键按钮和无权限路由拦截
    - Files: `frontend/src/components/Layout/AppLayout.tsx`, `frontend/src/components/Layout/ProjectLayout.tsx`, `frontend/src/pages/Documents/index.tsx`, `frontend/src/pages/Members/index.tsx`, `frontend/src/App.tsx`

- [ ] Task: 完成集成回归验证
    - Acceptance: 关键后端用例、前端构建和手工权限路径验证全部通过；spec 中 Success Criteria 有可追踪的验证结果。
    - Verify: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -v; Pop-Location`
    - Verify: `Push-Location frontend; npm run build; Pop-Location`
    - Verify: 手工验证 `admin`、`validation_admin`、`owner`、`manager`、`member`、`viewer` 的关键路径
    - Files: `docs/specs/role-menu-permission-management.md`, `backend/tests/*`, `frontend/src/**/*`

## Open Questions

- 当前无阻塞实现的未决问题；若后续需要扩展到动态菜单节点、字段级权限或数据级权限，另开新 spec。
