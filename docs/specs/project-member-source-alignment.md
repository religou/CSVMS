# Spec: 项目成员来源与项目角色字典统一

## Assumptions I'm Making

1. 本次范围只覆盖现有 Web 前后端，不涉及外部组织架构同步、SSO 或移动端。
2. `project_role` 是受控系统字典，当前权限语义仍然只认 `owner`、`manager`、`member`、`viewer` 四个角色代码；字典管理可以调整显示名称、颜色、排序和启用状态，但不会在本次需求中引入全新权限语义。
3. 项目成员候选人来源于系统管理中的用户数据，也就是 `users` 表及“用户管理”维护的人员，而不是项目内自建一套人员主数据。
4. 项目负责人、项目经理和系统管理员都应能完成“查找候选用户并添加到项目”的流程，不能因为调用管理员接口而被额外卡住。
5. 现有项目成员数据需要保持兼容，不能因为这次来源统一而让已有项目无法查看或编辑成员。

## Objective

统一项目成员管理的两套来源定义：

- 项目内角色以字典管理中的 `project_role` 为唯一业务来源，前后端都围绕字典代码和字典展示信息工作。
- 项目内人员以系统管理中的用户为唯一业务来源，项目成员只是“项目与系统用户之间的关系”，不是独立人员档案。

用户故事：

- 作为系统管理员，我希望项目成员角色与字典管理保持一致，这样角色名称、顺序和显示样式只需要维护一处。
- 作为项目负责人或项目经理，我希望能直接从系统用户中选择成员加入项目，而不是依赖管理员专用接口。
- 作为实施人员，我希望后端也按同一来源校验角色和成员，避免前端能选、后端不能存，或者前端展示与后端权限不一致。

当前已知缺口：

- [frontend/src/pages/Members/index.tsx](frontend/src/pages/Members/index.tsx#L100) 通过 `adminService.listUsers` 读取候选人员，这条接口面向系统管理，天然带有管理员角色限制。
- [backend/app/models/project.py](backend/app/models/project.py#L25) 和 [backend/app/schemas/project.py](backend/app/schemas/project.py#L22) 仍使用硬编码 `ProjectRole` 枚举，后端没有真正把 `project_role` 字典当作来源。

## Tech Stack

- Backend: Python 3.14, FastAPI, SQLAlchemy 2, Alembic
- Frontend: React 18, TypeScript, Ant Design 5, Zustand, Vite
- Testing: pytest + aiosqlite（后端）, Vitest + Testing Library（前端可用但当前覆盖较少）

## Commands

- Backend tests: `Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -v; Pop-Location`
- Frontend tests: `Push-Location frontend; npm run test -- --run; Pop-Location`
- Frontend build: `Push-Location frontend; npm run build; Pop-Location`
- Frontend lint: `Push-Location frontend; npm run lint; Pop-Location`
- Backend dev server: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir c:/Users/zhouek/Work/SelfProject/CSVS/backend`
- Frontend dev server: `Push-Location frontend; npm run dev; Pop-Location`

## Project Structure

- `backend/app/api/v1/projects.py` → 项目与项目成员相关 API
- `backend/app/services/project_service.py` → 项目成员权限和成员关系业务逻辑
- `backend/app/models/project.py` → 项目与项目成员数据模型
- `backend/app/schemas/project.py` → 项目成员请求/响应契约
- `backend/app/api/v1/dictionary.py` → 字典数据读取入口
- `backend/app/api/v1/admin.py` → 系统用户管理接口，当前被项目成员页错误复用
- `frontend/src/pages/Members/index.tsx` → 项目成员页面
- `frontend/src/services/projects.ts` → 项目成员前端服务层
- `frontend/src/hooks/useDictItems.ts` → 字典选项读取 Hook
- `backend/tests/` → 后端 API 与服务回归测试
- `frontend/src/**/*.test.tsx` → 前端组件与交互测试（本次变更建议补齐）
- `docs/specs/project-member-source-alignment.md` → 本规格文档

## Code Style

目标实现保持当前项目的路由薄层 + 服务层封装风格，接口负责鉴权和序列化，业务规则集中在 service：

```python
@router.get("/{project_id}/member-candidates", response_model=list[ProjectMemberCandidateResponse])
async def list_member_candidates(
    project_id: str,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = _get_service(db, current_user)
    users = await service.list_member_candidates(project_id, current_user.id, keyword=keyword)
    return [ProjectMemberCandidateResponse.model_validate(user) for user in users]
```

约定：

- API 返回角色代码，由前端通过字典映射 label 和颜色，不在前端硬编码角色中文名。
- 项目成员相关权限判断统一放在 `ProjectService`，不要在页面里复制一套后端规则。
- 如果角色来源改为字典动态校验，请优先在后端封装“读取并校验字典角色”的共享函数，而不是在多个路由里散落查询逻辑。

## Testing Strategy

- 后端使用 pytest，新增或补齐 `backend/tests/test_projects.py`，覆盖项目成员候选用户读取、成员新增、成员改角色、成员移除、权限校验和非法角色代码校验。
- 后端至少要有一条回归测试证明：项目负责人或项目经理在不具备 `admin`/`validation_admin` 系统角色时，仍可以拿到项目成员候选用户列表。
- 后端至少要有一条回归测试证明：角色代码必须来自 `project_role` 字典；禁用或不存在的角色代码会被拒绝。
- 前端优先补 `frontend/src/pages/Members` 的交互测试，验证候选用户来自项目接口而非管理员接口，且角色下拉与标签展示来自字典项。
- 如果本次不补前端自动化测试，至少要执行 `npm run build`、`npm run lint`，并手工验证“负责人/经理打开添加成员弹窗”这一关键路径。

## Boundaries

- Always: 项目成员候选人必须来自系统用户主数据；项目角色显示与校验必须使用 `project_role` 字典；后端权限校验必须独立于前端存在；已有项目成员关系必须可兼容读取。
- Ask first: 是否允许字典管理新增第五种项目角色代码；是否允许禁用或锁定用户继续被添加为项目成员；如果需要把数据库中的项目角色字段从枚举迁移为字符串，先确认迁移方案和兼容窗口。
- Never: 在项目成员页继续依赖 `/admin/users` 作为候选用户来源；在项目模块里维护第二套人员主数据；允许前端可选但后端无语义的角色代码直接入库；通过跳过权限校验来绕过项目经理/负责人取数问题。

## Success Criteria

1. 项目成员页面的角色下拉、角色标签和角色代码校验都以 `project_role` 字典为准，前后端不再各自维护一套角色定义。
2. 项目负责人、项目经理和系统管理员都可以读取项目成员候选用户列表，不需要依赖系统管理专用的 `/admin/users` 权限。
3. 候选用户列表来源于系统用户管理的人员数据，并且不会重复返回已在当前项目中的成员。
4. 后端新增/修改项目成员角色时，会拒绝不存在、未启用或无权限语义的角色代码，并返回明确错误。
5. 现有四种项目角色 `owner`、`manager`、`member`、`viewer` 的权限行为保持不变：`owner` 可改角色，`owner`/`manager` 可加减成员，`admin` 仍可跨项目管理。
6. 项目详情和成员列表继续返回成员关联的系统用户名、姓名和角色代码，前端能正确显示角色标签与人员名称。
7. 相关后端回归测试通过，前端至少完成构建与 lint 验证；如果补了前端测试，新增场景也必须通过。

## Resolved Decisions

以下决策已确认，并在与前文假设冲突时以后者为准：

1. `project_role` 字典允许新增角色代码，新增角色的项目内权限语义由系统管理员定义。
2. 系统用户被禁用或锁定后，需要从“可添加成员”候选列表中移除；如果该用户已经是项目成员，需要保留历史成员关系。
3. 候选用户接口需要支持关键字搜索、分页和按系统角色过滤。

## Implementation Plan

### Overview

本次实现按“先统一后替换”的顺序推进：先补足项目角色的权限语义载体和项目成员候选人专用接口，再把项目成员页切换到新的后端契约，最后补齐字典管理 UI 和验证。这样可以把“项目角色来源统一”和“项目人员来源统一”拆成多个可回归、可验证的增量。

### Architecture Decisions

1. **项目角色持久化从枚举切换为字符串代码。**
   当前 [backend/app/models/project.py](backend/app/models/project.py#L25) 的 `ProjectRole` 枚举只能容纳四个固定值，无法承载新增字典角色。实现上将把 `ProjectMember.role` 迁移为字符串代码，后端通过项目角色字典解析其权限语义。

2. **项目角色的“显示属性”和“权限语义”分离建模。**
   当前 `DictItem.extra` 在多个页面里都被当成颜色字符串使用，不能继续塞进权限配置。实现上为字典项新增显式的 `permission_profile` 字段，仅在 `project_role` 类别中使用；`extra` 继续保留为颜色/展示信息，避免打坏已有状态字典和项目状态字典的消费方。

3. **项目成员候选用户改为项目域接口。**
   新增 `/projects/{project_id}/member-candidates`，由项目服务按 `owner`/`manager`/`admin` 权限控制，并直接从系统用户表读取候选人。接口负责排除已加入成员、禁用用户和锁定用户，同时支持关键字、分页和系统角色过滤。

4. **新增角色的权限语义采用“权限档位”而非自由表述。**
   为兼容现有 `owner`、`manager`、`member`、`viewer` 的后端权限判断，首版由字典项的 `permission_profile` 显式映射到上述四种能力档位之一。这样系统管理员可以新增角色代码和展示名称，但仍落在现有可验证的权限边界内。

### Implementation Order

1. 先扩展字典数据模型和 API 契约，让 `project_role` 能承载权限档位。
2. 再改项目成员后端：角色存储改为字符串、成员角色校验改为字典驱动、补项目成员候选用户接口。
3. 再切前端成员页：移除对 `/admin/users` 的依赖，接入新候选接口与筛选参数。
4. 最后补字典管理页的项目角色权限档位编辑能力，并完成构建、lint 与关键回归验证。

### Risks and Mitigations

| Risk                                                        | Impact | Mitigation                                                                       |
| ----------------------------------------------------------- | ------ | -------------------------------------------------------------------------------- |
| `ProjectMember.role` 从枚举切到字符串会影响已有成员数据读取 | High   | 通过 Alembic 迁移做兼容转换；先补后端回归测试覆盖旧角色值读取与更新              |
| `DictItem.extra` 目前被广泛当颜色字段使用                   | High   | 不复用 `extra`，改为新增 `permission_profile` 可选字段，保持现有消费者不变       |
| 候选用户查询如果无分页会在用户量增长后退化                  | Medium | 接口首版即支持 `keyword`、`page`、`page_size`、`system_role`，前端采用服务端筛选 |
| 新增项目角色代码但没有权限档位会导致不可预期行为            | Medium | 后端创建/更新成员时强制校验 `permission_profile`；字典管理页保存时也要求填写     |

### Checkpoints

#### Checkpoint A: 字典契约完成后

- [ ] 字典 API 能返回并更新 `permission_profile`
- [ ] 现有非项目角色字典读取不受影响
- [ ] 后端相关新增测试通过

#### Checkpoint B: 项目成员后端完成后

- [ ] 项目成员角色读写改为字典驱动
- [ ] 候选用户接口可被负责人/经理/admin 正常调用
- [ ] `backend` 测试通过

#### Checkpoint C: 前端接入完成后

- [ ] 项目成员页不再调用 `/admin/users`
- [ ] 搜索、分页、系统角色过滤可用
- [ ] 前端 build 和 lint 通过

## Task Breakdown

### Phase 1: Foundation

#### Task 1: 扩展字典项权限档位契约

**Description:**
为字典项模型、Schema、字典 API 和数据库迁移增加 `permission_profile` 字段，使 `project_role` 可以在不复用 `extra` 的前提下声明其权限档位。

**Acceptance criteria:**

- [ ] `dict_items` 持久层支持可空 `permission_profile`
- [ ] 字典读写接口返回并接受 `permission_profile`
- [ ] `project_role` 项在缺少 `permission_profile` 时可被识别并在后续业务校验中拒绝使用

**Verification:**

- [ ] 后端测试通过：`Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -k "dict or project" -v; Pop-Location`
- [ ] 迁移可执行：`Push-Location backend; alembic upgrade head; Pop-Location`

**Dependencies:** None

**Files likely touched:**

- `backend/app/models/dictionary.py`
- `backend/app/schemas/dictionary.py`
- `backend/app/api/v1/dictionary.py`
- `backend/alembic/versions/*`
- `backend/app/scripts/seed_dict.py`

**Estimated scope:** Medium

#### Task 2: 为项目角色字典管理补权限档位编辑能力

**Description:**
更新字典管理页与前端字典类型，让系统管理员在维护 `project_role` 时可以查看和编辑 `permission_profile`，并保留 `extra` 作为颜色展示字段。

**Acceptance criteria:**

- [ ] `project_role` 项可在管理界面配置权限档位
- [ ] 非 `project_role` 类别不强制显示该字段
- [ ] 现有颜色字段继续可见且不受权限档位编辑影响

**Verification:**

- [ ] 前端 build 通过：`Push-Location frontend; npm run build; Pop-Location`
- [ ] 前端 lint 通过：`Push-Location frontend; npm run lint; Pop-Location`

**Dependencies:** Task 1

**Files likely touched:**

- `frontend/src/pages/Admin/DictManagement.tsx`
- `frontend/src/services/dictionary.ts`
- `frontend/src/i18n/*.json`

**Estimated scope:** Medium

### Phase 2: Core Backend

#### Task 3: 将项目成员角色改为字典驱动的字符串代码

**Description:**
把项目成员角色从硬编码枚举改为字符串存储，并在 `ProjectService` 中集中解析 `project_role` 字典与 `permission_profile`，保证新增角色代码也能落在既有权限档位内运行。

**Acceptance criteria:**

- [ ] `ProjectMember.role` 不再依赖 SQLAlchemy `Enum(ProjectRole)`
- [ ] 成员新增、角色变更、权限检查都通过字典角色解析器完成
- [ ] 缺失、禁用或未配置 `permission_profile` 的角色代码会被拒绝

**Verification:**

- [ ] 新增后端回归测试通过：`Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -k "project" -v; Pop-Location`

**Dependencies:** Task 1

**Files likely touched:**

- `backend/app/models/project.py`
- `backend/app/schemas/project.py`
- `backend/app/services/project_service.py`
- `backend/app/api/v1/projects.py`
- `backend/tests/test_projects.py`

**Estimated scope:** Medium

#### Task 4: 新增项目成员候选用户接口

**Description:**
在项目域下新增成员候选用户接口，按项目管理权限返回可选系统用户，并支持关键字、分页和系统角色过滤，替代前端当前对管理员用户列表的误用。

**Acceptance criteria:**

- [ ] `owner`、`manager`、`admin` 能调用候选接口
- [ ] 接口排除已在项目中的成员、禁用用户和锁定用户
- [ ] 接口支持 `keyword`、`page`、`page_size`、`system_role`

**Verification:**

- [ ] 后端测试通过：`Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -k "member_candidates or project" -v; Pop-Location`

**Dependencies:** Task 3

**Files likely touched:**

- `backend/app/api/v1/projects.py`
- `backend/app/services/project_service.py`
- `backend/app/schemas/project.py`
- `backend/tests/test_projects.py`

**Estimated scope:** Medium

### Phase 3: Frontend Integration

#### Task 5: 项目成员页切换到项目候选用户接口

**Description:**
更新项目成员页和前端项目服务层，改为调用项目候选用户接口，并在弹窗中支持关键字搜索、分页加载和系统角色过滤。

**Acceptance criteria:**

- [ ] `MembersPage` 不再依赖 `adminService.listUsers`
- [ ] 候选用户列表支持服务端搜索和分页
- [ ] 系统角色过滤条件可传到后端接口

**Verification:**

- [ ] 前端 build 通过：`Push-Location frontend; npm run build; Pop-Location`
- [ ] 前端 lint 通过：`Push-Location frontend; npm run lint; Pop-Location`
- [ ] 手工检查：负责人/经理打开“添加成员”弹窗可正常看到候选用户

**Dependencies:** Task 4

**Files likely touched:**

- `frontend/src/pages/Members/index.tsx`
- `frontend/src/services/projects.ts`
- `frontend/src/services/admin.ts`

**Estimated scope:** Medium

#### Task 6: 收口项目角色展示与回归验证

**Description:**
确保成员页、项目详情和相关字典展示都按新的项目角色契约工作，并完成后端全量测试与前端构建检查。

**Acceptance criteria:**

- [ ] 角色标签展示继续来自 `project_role` 字典
- [ ] 新增角色代码在成员页能正确展示其标签和颜色
- [ ] 全部成功标准已覆盖到测试或手工验证项

**Verification:**

- [ ] 后端全量测试：`Push-Location backend; C:/Users/zhouek/APP/Python/3.14.3/python.exe -m pytest tests/ -v; Pop-Location`
- [ ] 前端构建：`Push-Location frontend; npm run build; Pop-Location`
- [ ] 前端 lint：`Push-Location frontend; npm run lint; Pop-Location`

**Dependencies:** Task 5

**Files likely touched:**

- `frontend/src/pages/Members/index.tsx`
- `frontend/src/hooks/useDictItems.ts`
- `frontend/src/pages/Projects/index.tsx`
- `frontend/src/pages/Admin/DictManagement.tsx`
- `backend/tests/test_projects.py`

**Estimated scope:** Medium
