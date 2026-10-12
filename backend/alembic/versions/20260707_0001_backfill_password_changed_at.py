"""backfill password_changed_at for existing users

新增“首次登录强制改密”语义前，users.password_changed_at 为 NULL 既可能
表示“通过管理员邀请创建、尚未修改初始密码”，也可能只是历史遗留的空值
（该字段此前从未被管理员创建/重置路径写入）。为避免把既有正常使用系统
的用户误判为待强制改密，本迁移把迁移执行时仍为 NULL 的用户，回填为
COALESCE(updated_at, created_at)：视为“这批既有用户已经在用自己的密码，
不追溯要求改密”。迁移之后新建的邀请用户才会保持 NULL 并触发强制改密。

Revision ID: 20260707_0001
Revises: 20260706_0001
Create Date: 2026-07-07 00:01:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260707_0001"
down_revision = "20260706_0001"
branch_labels = None
depends_on = None


def _validate_schema(bind) -> None:
    inspector = sa.inspect(bind)
    if "users" not in set(inspector.get_table_names()):
        raise RuntimeError("密码改密回填迁移缺少必要数据表: users")

    required_columns = {"id", "password_changed_at", "updated_at", "created_at"}
    actual_columns = {
        column["name"] for column in inspector.get_columns("users")
    }
    missing_columns = sorted(required_columns - actual_columns)
    if missing_columns:
        raise RuntimeError(
            "密码改密回填迁移缺少必要字段: "
            + ", ".join(f"users.{name}" for name in missing_columns)
        )


def upgrade_data(bind: sa.engine.Connection) -> None:
    """把仍为 NULL 的 password_changed_at 回填为 COALESCE(updated_at, created_at)。"""
    _validate_schema(bind)

    users = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("password_changed_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
        sa.column("created_at", sa.DateTime),
    )

    bind.execute(
        sa.update(users)
        .where(users.c.password_changed_at.is_(None))
        .values(
            password_changed_at=sa.func.coalesce(
                users.c.updated_at, users.c.created_at
            )
        )
    )


def upgrade() -> None:
    upgrade_data(op.get_bind())


def downgrade() -> None:
    # 回填后的既有值与本迁移执行前的原始 NULL 不可区分，因此不可逆。
    pass
