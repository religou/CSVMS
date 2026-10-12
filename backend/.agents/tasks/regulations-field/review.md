# 符合法规 multi-select on the System form, backed by a new 法规 dictionary

The change adds a 符合法规 field to the 系统管理 add/edit modal. Its options come from a new `regulation` dictionary category (法规, 18 FDA / EU-EMA / ICH / PIC/S / MHRA / WHO / NMPA / GAMP items). The selected item codes are stored as a JSON list in a new nullable `systems.regulations` column. One Alembic migration (`20261012_0001`, on top of head `20260708_0001`) adds the column and seeds the dictionary idempotently. `seed_dict.py` carries the same data, and a test keeps the two copies identical. On the frontend, the field uses the existing `useDictItems` hook and sits between the GxP/GAMP5 row and 系统描述. The 法规 tab is appended last in 字典管理.

Watch for: nothing blocking. The open gaps are minor. Downgrade deletes admin-added 法规 items too (confirmed, by design). The API stores any string list without checking it against the dictionary (confirmed, deliberate per plan). The 法规 tab position in 字典管理 has no test and was not checked in a browser (confirmed).

**Verdict**: APPROVED

## High-level view

The migration is a frozen snapshot, in the same style as `20260601_0004`. Each part is guarded: the column is added only if the inspector does not find it, the category is inserted only if code `regulation` is missing, and only missing `(category_id, code)` items are inserted, with `uuid4` ids. The downgrade removes every item in the category, then the category, then the column. `down_revision` is the current head `20260708_0001`. The coder's evidence covers a single head, upgrade, downgrade/upgrade round trip, and a stamp-then-re-upgrade run that created no duplicates.

The backend contract is a list of codes. `SystemCreate`/`SystemUpdate` accept `list[str] | None`. `_system_response` normalizes NULL to `[]`, so existing rows (which stay NULL) and new rows created without the field both return an empty array. PATCH keeps `exclude_unset` semantics: leaving the field out keeps the stored value, and `[]` clears it. Tests cover all four cases.

On the frontend, the Select is `mode="multiple"`, searches by label, and gets its options from `useDictItems('regulation')` (enabled items only). The GxP/GAMP5 selects use hard-coded constants, so this hook is the dictionary-backed pattern the codebase already uses elsewhere. Edit mode fills the field with `system.regulations ?? []`.

<details>
<summary>Issues (4)</summary>

1. **Downgrade deletes admin-added 法规 items** — `downgrade()` deletes every `dict_items` row in the `regulation` category, not only the 18 seeded ones, and drops `systems.regulations` along with any saved selections (confirmed). This is a deliberate choice so the FK does not block the category delete. Non-blocking: before any downgrade on a DB that has real data, note in the migration docstring or runbook that the downgrade loses data.
2. **No server-side check of regulation codes** — `SystemCreate/SystemUpdate.regulations` accept any list of any strings, with no check against the dictionary and no length bound (confirmed). The endpoint is admin-only and the plan accepts this. Non-blocking: if strict consistency is needed later, validate codes against enabled `regulation` items.
3. **Disabled items show as raw codes** — `useDictItems` loads only enabled items, so a system that still stores a later-disabled code shows the bare code as a tag in edit mode (confirmed, plan-accepted). Non-blocking: if this becomes a problem, pass `enabledOnly: false` and mark disabled options.
4. **法规 tab order has no test** — `'regulation'` is appended to `CATEGORY_DISPLAY_ORDER`, but `DictManagement.test.tsx` does not assert the tab order, and `verification.md` says the 字典管理 page was not checked manually (confirmed). Non-blocking: add an assertion that the 法规 tab is rendered last.

</details>

<details>
<summary>Details</summary>

### Migration 20261012_0001: idempotency and the downgrade blast radius

If an admin has deleted one of the seeded items, a re-run of the upgrade (for example after a stamp) adds it back. Normal Alembic use runs the migration only once, so this rarely matters.

The downgrade is not symmetric with the upgrade. The upgrade inserts only the 18 known codes, but the downgrade deletes `WHERE category_id = :id`. That includes any items admins have added. It then drops `systems.regulations` and every saved selection with it (confirmed, `downgrade()`). The plan chose this on purpose, because otherwise the `dict_items.category_id` FK blocks the category delete. The alternative would be to keep the category when other items exist. Either way, a downgrade on a populated DB loses data, and nothing in the migration warns about that. The only downgrade run was the manual one on the dev DB, before any system had saved regulations.

### Code list contract between API and form

```
Select(mode=multiple, options=useDictItems('regulation'))
   │  values: ["fda_21cfr_part11", ...]   (undefined if untouched on create)
   ▼
POST / PATCH /api/v1/systems ── SystemCreate/Update.regulations: list[str] | None
   ▼
systems.regulations JSON (NULL for legacy rows)
   ▼
_system_response → regulations or []  → SystemItem.regulations: string[]
```

A PATCH with an explicit `null` stores NULL, and NULL reads back as `[]`. So NULL and empty cannot be told apart through the API. Nothing in the plan needs that distinction.

No check ties the stored codes to the dictionary (confirmed). An admin client can store `["anything"]`, and the UI shows it as a raw tag. Codes whose dictionary item was later disabled show the same way, because `useDictItems` defaults to `enabledOnly: true`. The plan accepts both.

### Test coverage

A drift test loads the migration module by path and asserts that its `down_revision`, category metadata and `REGULATION_ITEMS` match `SEED_DATA` exactly. That test is what makes the deliberate duplication safe. The backend tests cover the API round trip and the PATCH cases. The frontend tests cover option loading, the field's position, the edit-mode fill-in and the save payload.

Not tested: the downgrade path in automated tests (it was only exercised once, by hand, on the dev DB, before any system had data); the 法规 tab position in 字典管理; the create-mode payload from the UI.

### Bundled earlier edits

The same diff contains the edits for earlier requests in this session. 版本号 moved above the vendor field, the vendor label changed to 供应商名称 in both the form and the list column, and `CATEGORY_DISPLAY_ORDER` / `sortCategoriesForDisplay` were added with `system_role` between `doc_type` and `project_role`. Each matches what the user asked for. They will land in the same commit unless they are split out.

</details>

<details>
<summary>File map</summary>

- `backend/alembic/versions/20261012_0001_add_regulations_to_systems.py` (new): adds `systems.regulations` JSON column; seeds the `regulation` category and 18 items idempotently; reversible downgrade.
- `backend/app/models/system.py`: `regulations` JSON column on `System`.
- `backend/app/schemas/system.py`: `regulations` on Create/Update (optional list) and Response (default `[]`).
- `backend/app/api/v1/systems.py`: `_system_response` returns `regulations or []`.
- `backend/app/scripts/seed_dict.py`: `regulation` category with the same 18 items.
- `backend/tests/test_systems.py` (new): create/update round-trip tests.
- `backend/tests/test_dictionary.py`: seed test for the regulation category; migration/seed drift test.
- `frontend/src/services/systems.ts`: `regulations` on `SystemItem` and the Create/Update payload types.
- `frontend/src/pages/Systems/index.tsx`: 符合法规 multi-select, edit-mode fill-in; also the earlier version/vendor reorder and 供应商名称 label.
- `frontend/src/pages/Systems/index.test.tsx` (new): option loading, field position, save payload.
- `frontend/src/pages/Admin/DictManagement.tsx`: `CATEGORY_DISPLAY_ORDER` (from the earlier request) with `'regulation'` appended.

Full diff: `git diff` plus the untracked files above, in `c:\Users\zhouek\Work\SelfProject\CSVMS`.

</details>
