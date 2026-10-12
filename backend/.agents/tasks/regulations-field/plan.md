# Implementation Plan: 符合法规 (regulations) field on System form

Repo: `c:\Users\zhouek\Work\SelfProject\CSVMS` (branch `main`, no worktree). Windows + PowerShell.
Python: `c:\Users\zhouek\Work\SelfProject\CSVMS\.venv\Scripts\python.exe` (below: `$PY`). Do NOT commit.
Dev servers already running: backend uvicorn `--reload` on :8000, Vite on :5173. Do not start duplicates.

## Context found during exploration

- Alembic head is `20260708_0001` (confirmed with `$PY -m alembic heads` from `backend`). Migrations 0706/0707/0708 and `app/core/permission_catalog.py` are untracked restores; leave them alone.
- `frontend/src/pages/Systems/index.tsx` and `frontend/src/pages/Admin/DictManagement.tsx` already have uncommitted edits from earlier requests (version above vendor, label 供应商名称, `CATEGORY_DISPLAY_ORDER` with system_role between doc_type and project_role). Keep those edits; build on them.
- The GxP/GAMP5 Selects use hard-coded constants, not the dict. The dict-backed pattern in this codebase is the hook `useDictItems(categoryCode)` in `frontend/src/hooks/useDictItems.ts` (returns `{ items, options }`, options = `{ value: item.code, label: item.label }`, enabled-only by default). It is used in `pages/Workflows/index.tsx`, `pages/Members/index.tsx`, `pages/Documents/index.tsx`. Use it.
- System API is `backend/app/api/v1/systems.py`: POST `/api/v1/systems`, PATCH `/api/v1/systems/{id}` (not PUT), GET `/api/v1/systems/{id}`. Responses are built by `_system_response()` (explicit dict), so the new field must be added there. Create uses `System(**data.model_dump())`; update uses `setattr` over `model_dump(exclude_unset=True)`; no separate service layer.
- JSON column precedent: `DictItem.permission_codes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)` and migration `20260601_0005` (`sa.JSON()`). Migration seeding precedent: `20260601_0004` (`sa.table(...)`, select-then-insert, `uuid.uuid4()` ids, `datetime.now(timezone.utc)`). Models use `generate_uuid()` = `str(uuid.uuid4())` and CHAR(36).
- `DictItem` limits: code String(50), label String(200). All 18 items in `regulation-items.md` fit (longest label ≈115 chars).
- Backend tests: pytest + SQLite in-memory (`backend/tests/conftest.py`, tables via `Base.metadata.create_all`, so tests see model changes without migrations). Auth helpers pattern: `_create_admin` / `_login` / `_auth_header` in `backend/tests/test_dictionary.py`. There is no `tests/test_systems.py` yet. The full suite takes >10 min (hypothesis); run targeted files.
- Frontend tests: vitest + Testing Library; mocking pattern in `src/pages/Projects/index.test.tsx` and `src/pages/Admin/DictManagement.test.tsx` (`vi.mock('@/services/...')`, `useAuthStore.setState({... roles: ['admin'] })`). No Systems page test exists.
- `npx tsc --noEmit -p .` baseline (before this work): 24 errors, all in `src/App.test.tsx`, `src/pages/Dashboard/index.test.tsx`, `src/pages/Home/index.test.tsx`, `src/pages/Login/index.test.tsx`, `src/pages/Workflows/index.tsx`, `src/utils/stageDisplay.test.ts`, `src/utils/ursDisplay.test.ts`. None in files this plan touches.
- No admin password is documented (`deploy/local.md` only has DB creds). For live API checks, mint a JWT with `app.core.security.create_access_token(<admin user id>)`; `get_current_user` only checks `sub`/`type`, active and not locked.

## Design decisions

- Item data is duplicated in the migration (frozen snapshot) and in `seed_dict.py`, matching the existing migrations that never import seed scripts. A backend test asserts the two lists are identical so they cannot drift.
- Migration file `backend/alembic/versions/20261012_0001_add_regulations_to_systems.py`, revision `20261012_0001`, down_revision `20260708_0001` (date matches the research date of the item list).
- Upgrade is idempotent: adds the column only if `systems.regulations` is missing (inspector), creates the category only if code `regulation` is missing, inserts only items whose `(category_id, code)` is missing. Existing systems keep NULL.
- Downgrade removes everything in the `regulation` category (all its `dict_items`, then the category row) and drops the column. Deleting all items, not just the seeded codes, is needed because admins may add items and the FK would block the category delete.
- `SystemCreate`/`SystemUpdate` take `regulations: list[str] | None = None`. `SystemResponse.regulations: list[str] = []`, and `_system_response` returns `system.regulations or []`, so the frontend always gets an array. No server-side validation of codes against the dict (a code may later be disabled; the form shows the raw code then, which is acceptable).
- Frontend `SystemItem.regulations: string[]`; Create/Update data `regulations?: string[]`. Edit mode sets `regulations: system.regulations ?? []`. Saving sends whatever the Select holds (array; `[]` after clearing). No list-table column (optional, skipped).
- Select: `mode="multiple"`, `allowClear`, `optionFilterProp="label"` (search by label instead of code; labels are long), placeholder `选择符合的法规`.

## Steps

- [ ] 1. Add the Alembic migration and apply it to the dev DB.
      Create `backend/alembic/versions/20261012_0001_add_regulations_to_systems.py` with header docstring (Revision ID / Revises / Create Date, in the style of `20260701_0002_add_stage_to_projects.py`), `revision = "20261012_0001"`, `down_revision = "20260708_0001"`.
      Module constants: `REGULATION_CATEGORY = {"code": "regulation", "name": "法规", "description": "系统需符合的法规/指南", "is_system": True}` and `REGULATION_ITEMS` = list of 18 dicts `{"code", "label", "description", "sort_order"}` copied exactly from the table in `backend/.agents/tasks/regulations-field/regulation-items.md` (sort_order 10..180).
      `upgrade()`: `bind = op.get_bind()`; `inspector = sa.inspect(bind)`; if `"regulations"` not in `[c["name"] for c in inspector.get_columns("systems")]` then `op.add_column("systems", sa.Column("regulations", sa.JSON(), nullable=True))`. Define lightweight `sa.table` for `dict_categories` (id, code, name, description, is_system, created_at) and `dict_items` (id, category_id, code, label, description, sort_order, is_enabled, extra, permission_profile, permission_codes, created_at). Select category id by code; if none, insert with `id=str(uuid.uuid4())`, `created_at=datetime.now(timezone.utc)`. Select existing item codes for that category; insert each missing item with new uuid, `is_enabled=True`, `extra/permission_profile/permission_codes=None`, `created_at=now`.
      `downgrade()`: look up category id; if present, `DELETE FROM dict_items WHERE category_id = :id`, then delete the category; then drop column `systems.regulations` if it exists.
      Files: `backend/alembic/versions/20261012_0001_add_regulations_to_systems.py`
      Verify (cwd `backend`):
      - `$PY -m alembic heads` → `20261012_0001 (head)` (single head).
      - `$PY -m alembic upgrade head` exits 0; `$PY -m alembic current` → `20261012_0001 (head)`.
      - Reversibility/idempotency round-trip (run now, before any system has regulations saved): `$PY -m alembic downgrade -1` → current `20260708_0001`; `$PY -m alembic upgrade head` → back to `20261012_0001`.
      - Read-only DB check via a one-off `$PY -c` using `sqlalchemy.create_engine(settings.DATABASE_URL_SYNC)` (`from app.core.config import settings`): `systems.regulations` column exists; exactly 1 `dict_categories` row with code `regulation` and `is_system=1`; 18 `dict_items` for it.

- [ ] 2. Add `regulations` to the System model, schemas and API response. Depends on step 1 (the --reload server will query the new column as soon as the model changes).
      - `backend/app/models/system.py`: import `JSON` from sqlalchemy; add `regulations: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)` after `gamp5_category`.
      - `backend/app/schemas/system.py`: `regulations: list[str] | None = None` in `SystemCreate` and `SystemUpdate` (after `gamp5_category`); `regulations: list[str] = []` in `SystemResponse`.
      - `backend/app/api/v1/systems.py`: in `_system_response`, add `"regulations": system.regulations or [],` after `gamp5_category`. Create/update need no other change (`model_dump` / `setattr` already pass the field through).
      Files: the three above.
      Verify (cwd `backend`): `$PY -c "import app.main"` succeeds; `$PY -m pytest tests/test_traceability.py -q -k "test_dashboard or end_to_end"` (existing tests that POST /api/v1/systems) still pass.

- [ ] 3. Add the `regulation` category to `SEED_DATA`.
      Append to `SEED_DATA` in `backend/app/scripts/seed_dict.py` a category dict `{"code": "regulation", "name": "法规", "description": "系统需符合的法规/指南", "is_system": True, "items": [...]}` with the same 18 items (`code`, `label`, `description`, `sort_order`) as the migration, same order. `seed_dict()` already handles `description` via `DictItem(**item_data)`; no logic change.
      Files: `backend/app/scripts/seed_dict.py`
      Verify (cwd `backend`): `$PY -m pytest tests/test_dictionary.py -q -k seed` → the two existing seed tests pass.

- [ ] 4. Add backend tests.
      - New `backend/tests/test_systems.py` (copy the `_create_admin` / `_login` / `_auth_header` helper pattern from `tests/test_dictionary.py`, with its own username e.g. `sys-admin`). Tests:
        a. `test_create_system_with_regulations_round_trip`: POST `/api/v1/systems` with `regulations: ["fda_21cfr_part11", "eu_gmp_annex11"]` → 200 and response has that list; GET `/api/v1/systems/{id}` returns the same list; GET `/api/v1/systems` list item contains it.
        b. `test_update_system_regulations`: create without `regulations` → response `regulations == []`; PATCH with `["ich_q9_r1"]` → returned and persisted (GET); PATCH with `[]` → `[]`; PATCH with only `{"name": "x"}` leaves regulations unchanged.
      - In `backend/tests/test_dictionary.py` add:
        c. `test_seed_dict_creates_regulation_category`: same monkeypatch pattern as `test_seed_dict_creates_project_stage_category`; assert category `regulation` exists with `name == "法规"`, `is_system is True`, 18 items, item codes include `fda_21cfr_part11` and `eu_gmp_annex11`; then with an admin token GET `/api/v1/dict/categories/regulation/items` returns 18 items ordered by `sort_order`.
        d. `test_regulation_migration_items_match_seed_data`: load the migration module with `importlib.util.spec_from_file_location` from `Path(__file__).parents[1] / "alembic/versions/20261012_0001_add_regulations_to_systems.py"`; assert its `down_revision == "20260708_0001"`, its `REGULATION_CATEGORY` matches the seed category (code/name/description/is_system), and its `REGULATION_ITEMS` equals the seed category's `items` list.
      Files: `backend/tests/test_systems.py` (new), `backend/tests/test_dictionary.py`
      Verify (cwd `backend`): `$PY -m pytest tests/test_systems.py tests/test_dictionary.py -q` → all pass. Then `$PY -m pytest -q -k "system or dict"` (timeout ~15 min) → no failures.

- [ ] 5. Frontend types and the 符合法规 form field.
      - `frontend/src/services/systems.ts`: `SystemItem` gets `regulations: string[]`; `CreateSystemData` and `UpdateSystemData` get `regulations?: string[]`.
      - `frontend/src/pages/Systems/index.tsx`:
        - `import { useDictItems } from '@/hooks/useDictItems'`; inside the component `const { options: regulationOptions } = useDictItems('regulation')`.
        - In `openModal`, replace `form.setFieldsValue(system)` with `form.setFieldsValue({ ...system, regulations: system.regulations ?? [] })`.
        - Insert, between the closing `</Row>` of the GxP/GAMP5 row and `<Form.Item name="description" label="系统描述">`:
          ```tsx
          <Form.Item name="regulations" label="符合法规">
              <Select
                  mode="multiple"
                  allowClear
                  placeholder="选择符合的法规"
                  optionFilterProp="label"
                  options={regulationOptions}
              />
          </Form.Item>
          ```
        - `handleSave` needs no change: `values` already carries `regulations` into create/update.
      Files: `frontend/src/services/systems.ts`, `frontend/src/pages/Systems/index.tsx`
      Verify (cwd `frontend`): `npx tsc --noEmit -p .` → still only the 24 baseline errors in the 7 baseline files; none in `services/systems.ts` or `pages/Systems/index.tsx`.

- [ ] 6. Show the 法规 tab last in 字典管理.
      Append `'regulation'` to the end of `CATEGORY_DISPLAY_ORDER` in `frontend/src/pages/Admin/DictManagement.tsx` (after `'project_status'`). Do not reorder the existing entries.
      Files: `frontend/src/pages/Admin/DictManagement.tsx`
      Verify (cwd `frontend`): `npx vitest --run src/pages/Admin/DictManagement.test.tsx` passes.

- [ ] 7. Add a Systems page vitest.
      New `frontend/src/pages/Systems/index.test.tsx`. Mock `@/services/systems` (list/get/create/update/delete; `list` resolves one system with `regulations: ['fda_21cfr_part11']`), `@/services/dictionary` (full method set as in `Projects/index.test.tsx`; `listItems` returns two regulation items for `'regulation'`, `[]` otherwise), and `@/services/admin` (`adminService.listUsers` resolves `{ data: [] }`). Set an admin user with `useAuthStore.setState` as in `DictManagement.test.tsx`. Tests:
        a. `dictService.listItems` is called with `'regulation'`.
        b. Click the row's edit button, the modal shows a 符合法规 label, and its position in the form label order is after `GAMP5 类别` and before `系统描述` (collect `.ant-modal .ant-form-item-label label` texts).
        c. In edit mode, click 保存 (`/保\s*存/`); `systemService.update` is called with the system id and `expect.objectContaining({ regulations: ['fda_21cfr_part11'] })`.
      Files: `frontend/src/pages/Systems/index.test.tsx` (new)
      Verify (cwd `frontend`): `npx vitest --run src/pages/Systems src/pages/Admin/DictManagement.test.tsx src/pages/Projects` passes; `npx tsc --noEmit -p .` shows no new errors (the new test file has none).

- [ ] 8. Live end-to-end check against the running dev servers (no new servers).
      From `backend`, with a temporary script under `backend/.agents/tasks/regulations-field/` (delete it afterwards) using `httpx` against `http://localhost:8000`:
      - Look up an active admin user id via `settings.DATABASE_URL_SYNC` (`SELECT u.id FROM users u JOIN user_roles ur ON ur.user_id = u.id JOIN roles r ON r.id = ur.role_id WHERE r.name = 'admin' AND u.is_active = 1 LIMIT 1`); mint a token with `create_access_token(user_id)`.
      - GET `/api/v1/dict/categories/regulation/items` → 200, 18 items, first code `fda_21cfr_part11`.
      - POST `/api/v1/systems` with a unique temporary code (e.g. `TMP-REG-<random>`) and `regulations: ["fda_21cfr_part11"]`; PATCH it with `["fda_21cfr_part11", "eu_gmp_annex11"]`; GET it and confirm the list; GET an existing system and confirm `regulations` is `[]` (not null); DELETE the temporary system.
      - Open http://localhost:5173 → 系统管理 → 新增系统 / 编辑: 符合法规 multi-select sits after the GxP/GAMP5 row and before 系统描述 and lists the 18 法规 labels; 字典管理 shows the 法规 tab last. (Manual; report if not checked.)
      Files: none kept.
      Verify: all API assertions pass; temporary system and script are removed; `git status` shows only the intended files changed/added (plus the pre-existing untracked migration restores and `.agents/`).

## Files touched (summary)

Backend: `alembic/versions/20261012_0001_add_regulations_to_systems.py` (new), `app/models/system.py`, `app/schemas/system.py`, `app/api/v1/systems.py`, `app/scripts/seed_dict.py`, `tests/test_systems.py` (new), `tests/test_dictionary.py`.
Frontend: `src/services/systems.ts`, `src/pages/Systems/index.tsx`, `src/pages/Systems/index.test.tsx` (new), `src/pages/Admin/DictManagement.tsx`.

## Notes / assumptions

- Item descriptions are kept exactly as in `regulation-items.md` (English text). Labels are bilingual and are what users see in the Select.
- If a regulation item is later disabled, systems that already reference it still store the code; the Select then shows the raw code as a tag. Acceptable for this scope.
