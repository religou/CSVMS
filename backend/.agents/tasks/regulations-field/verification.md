# Verification: 符合法规 (regulations) field

Date: 2026-10-12. Iteration 1 (no `review.json` existed). Nothing committed.
`$PY` = `c:\Users\zhouek\Work\SelfProject\CSVMS\.venv\Scripts\python.exe`. Backend commands ran from `backend`, frontend commands from `frontend`.

## Alembic (dev MySQL DB)

| Command | Result |
|---|---|
| `$PY -m alembic heads` (before writing the migration) | `20260708_0001 (head)`, which matches `alembic-recovery.md` |
| `$PY -m alembic heads` (after) | `20261012_0001 (head)`, single head |
| `$PY -m alembic upgrade head` | PASS: `Running upgrade 20260708_0001 -> 20261012_0001` |
| `$PY -m alembic current` | `20261012_0001 (head)` |
| `$PY -m alembic downgrade -1`, then `current` | PASS: current = `20260708_0001` |
| `$PY -m alembic upgrade head`, then `current` | PASS: current = `20261012_0001 (head)` |
| Idempotency: `$PY -m alembic stamp 20260708_0001`, then `upgrade head`, run while the column, category and items already existed | PASS: no error, and no duplicates were created |

Read-only DB check (one-off script through `settings.DATABASE_URL_SYNC`), run after each upgrade:
- `systems.regulations`: type `JSON`, nullable.
- `dict_categories` with code `regulation`: exactly 1 row (`法规`, `系统需符合的法规/指南`, `is_system=1`, id length 36).
- `dict_items` in that category: 18 rows, all 18 enabled.
- Existing systems with non-NULL `regulations`: 0 of 1 (existing data stays NULL).
- A one-off script parsed the table in `regulation-items.md` and compared it with `REGULATION_ITEMS` in the migration. The 18 code/label/description/sort_order rows are identical. The longest label is 113 chars (limit 200). The longest code is 27 chars (limit 50).

## Backend tests

| Command | Result |
|---|---|
| `$PY -c "import app.main"` | PASS |
| `$PY -m pytest tests/test_systems.py tests/test_dictionary.py -q` | PASS: 12 passed |
| `$PY -m pytest tests -k "system or dict" -q` | PASS: 25 passed, 190 deselected (2m37s) |

New and changed tests:
- `tests/test_systems.py` (new):
  - `test_create_system_with_regulations_round_trip` checks POST, then GET detail, then the GET list.
  - `test_update_system_regulations` checks four cases: a create without the field returns `[]`; a PATCH sets the value; a PATCH with only `name` leaves it unchanged; a PATCH with `[]` clears it.
- `tests/test_dictionary.py`:
  - `test_seed_dict_creates_regulation_category` checks that the seed creates the category and its 18 items, and that the API returns them in `sort_order` order.
  - `test_regulation_migration_items_match_seed_data` checks that the migration snapshot equals `SEED_DATA` and that `down_revision` is `20260708_0001`.

## Frontend

| Command | Result |
|---|---|
| `npx tsc --noEmit -p .` | 24 errors, all in the 7 baseline files (`App.test.tsx` 2, `Dashboard/index.test.tsx` 11, `Home/index.test.tsx` 2, `Login/index.test.tsx` 1, `Workflows/index.tsx` 2, `stageDisplay.test.ts` 1, `ursDisplay.test.ts` 5). This matches the baseline in `plan.md`. No errors in `services/systems.ts`, `pages/Systems/*` or `pages/Admin/DictManagement.tsx`. |
| `npx vitest --run src/pages/Systems src/pages/Admin/DictManagement.test.tsx src/pages/Projects` | PASS: 3 files, 4 tests |

The new test file `src/pages/Systems/index.test.tsx` covers three things:
- The page calls `dictService.listItems('regulation', true)`.
- In the 编辑系统 modal, the 符合法规 label comes after `GAMP5 类别` and before `系统描述`.
- Edit mode pre-fills the existing value (tag `FDA 21 CFR Part 11`), and 保存 calls `systemService.update('system-1', { ..., regulations: ['fda_21cfr_part11'] })`.

## Live API (running dev servers; no new servers started, no restart needed because `--reload` picked up the model change)

A temporary script used httpx with a JWT minted through `create_access_token(<active admin id>)`. No admin password is documented. The script was deleted afterwards.
- `GET /api/v1/dict/categories/regulation/items` returned 200 with 18 items. The first item is `fda_21cfr_part11`. PASS
- `POST /api/v1/systems` with `regulations: ["fda_21cfr_part11"]` returned 200 with the same list. PASS
- `PATCH /api/v1/systems/{id}` with `["fda_21cfr_part11","eu_gmp_annex11"]` returned 200. A following `GET` returned the same list. PASS
- `GET` on the existing system `HRTAU_EDC_001` returned `regulations: []` (not null). PASS
- The temporary system was deleted (200).

## UI

No browser tool was available. Vite on :5173 serves the transformed `src/pages/Systems/index.tsx` with status 200. The served code contains the `regulations` Form.Item and `useDictItems("regulation")`. The field position and the pre-filled value were checked in the vitest DOM test above, not in a real browser. Not checked manually: the 字典管理 page showing the 法规 tab last.
