# Alembic recovery: missing revision 20260708_0001

Status: RESOLVED. `alembic heads` and `alembic current` both report `20260708_0001 (head)`. `alembic upgrade head` now runs as a no-op.

## Root cause

Three migrations were missing from the repo, not just one. The DB is at `20260708_0001`, which needs `20260707_0001`, which needs `20260706_0001`. The source code chain stopped at `20260705_0001`.

All three were added in commit `332a272` ("修改了审批流", 2026-09-07 18:29), along with 60 other files. A later `git reset` to `HEAD~1` removed that commit from `main` (see `git reflog`, `HEAD@{2}`). The DB had already been migrated with that code. Afterwards, `main` moved on (Version 0.1.0, then a pull up to `88c264d`) without it. `332a272` still exists in the object store as a dangling commit.

## Recovered migrations

The `.pyc` files were disassembled first (16-byte header, `marshal.loads`, `dis`). The original sources were then found in `332a272`. Each restored file compiles to the same bytecode as its orphaned `.pyc`, checked recursively on `co_code`, `co_names`, `co_varnames` and `co_consts`.

### 20260706_0001 — materialize project role permissions (down_revision `20260705_0001`)
- `upgrade()`: data only, no DDL. Requires that the tables `dict_categories`, `dict_items`, `permissions`, `roles` and `role_permissions` exist with their expected columns. If not, it raises `RuntimeError`.
  - For each `project_role` dict item with empty or NULL `permission_codes`, it writes `default_project_role_permission_codes(permission_profile)`. Non-empty values are checked with `validate_project_role_permission_codes`.
  - It upserts every entry from `permission_seed_data()` into `permissions`. Matching is by `code`; new rows get a uuid4 `id`.
  - It gives the single `admin` role every permission in `default_system_role_permission_codes("admin")` that it does not already have, by inserting the missing `role_permissions` rows.
- `downgrade()`: no-op.
- It imports `app.core.permission_catalog`. That module was also removed by the reset.

### 20260707_0001 — backfill password_changed_at (down_revision `20260706_0001`)
- `upgrade()`: data only. Requires the `users` table with columns `id`, `password_changed_at`, `updated_at` and `created_at`. Runs `UPDATE users SET password_changed_at = COALESCE(updated_at, created_at) WHERE password_changed_at IS NULL`.
- `downgrade()`: no-op.

### 20260708_0001 — add project_role to workflow_steps (down_revision `20260707_0001`)
- `upgrade()`: `op.add_column("workflow_steps", sa.Column("project_role", sa.String(50), nullable=True))`. It then requires the tables `workflows`, `workflow_steps` and `workflow_template_steps`, and runs this MySQL UPDATE:
  ```sql
  UPDATE workflow_steps AS ws
  JOIN workflows AS w ON w.id = ws.workflow_id
  JOIN workflow_template_steps AS wts
      ON wts.template_id = w.template_id AND wts.step_order = ws.step_order
  SET ws.project_role = wts.project_role
  WHERE ws.project_role IS NULL AND w.status IN ('IN_PROGRESS', 'PENDING')
  ```
- `downgrade()`: `op.drop_column("workflow_steps", "project_role")`.

## Live DB state (checked read-only through `settings.DATABASE_URL_SYNC`, built from the `DB_*` keys in `.env`)

The DB already reflects all three migrations:
- `alembic_version` = `20260708_0001`.
- `workflow_steps.project_role` exists as nullable `VARCHAR(50)`. 2 of 8 rows are non-NULL.
- `users.password_changed_at` exists. 1 of 7 users is NULL, which is expected for an invited user created after the 0707 backfill.
- All 8 `project_role` dict items have `permission_codes` filled in, and `permissions` has 29 rows.

## Resolution

These four files were restored verbatim from `332a272` with `git restore --source=332a272`. They are untracked and not committed.
- `backend/alembic/versions/20260706_0001_materialize_project_role_permissions.py`
- `backend/alembic/versions/20260707_0001_backfill_password_changed_at.py`
- `backend/alembic/versions/20260708_0001_add_project_role_to_workflow_steps.py`
- `backend/app/core/permission_catalog.py`. This one is needed because Alembic imports every migration module, even for `heads` and `current`. It uses only the standard library, and no current app code imports it.

No stamp was run, `alembic_version` was not modified, and nothing was dropped.

Verification:
- `alembic heads`: returns `20260708_0001 (head)`.
- `alembic current`: returns `20260708_0001 (head)`.
- `alembic history`: shows the chain 0705 → 0706 → 0707 → 0708.
- `alembic upgrade head`: exits 0 and makes no changes.
- `import app.main`: succeeds.
- The full `pytest` run did not finish within 10 minutes. No test references these files or `permission_catalog`.

## Open item for the user (not acted on)

Commit `332a272` also held app changes that are still missing from `main`. These include approval-flow changes in `workflow_service.py` and `models/workflow.py`, `invitation_service.py`, the project and workflow notification services, the forced password change on first login, and frontend service changes. The DB schema includes that commit's changes, but the current code does not. This works today because the extra columns are nullable. Whether to restore that commit is a separate decision. It may conflict with the ADR-0004..0006 refactors. You can inspect it with `git show --stat 332a272`. It will be lost if git garbage-collects dangling objects, so create a branch from it if it might be needed: `git branch rescue/332a272 332a272`.
