"""personal finance planner tables

Revision ID: 0009_personal_finance_planner
Revises: 0008_client_web_social_fields
Create Date: 2026-04-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_personal_finance_planner"
down_revision: str | None = "0008_client_web_social_fields"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _idx(table: str, col: str) -> str:
    return f"ix_{table}_{col}"


def upgrade() -> None:
    op.create_table(
        "personal_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("account_type", sa.String(length=40), nullable=False, server_default="checking"),
        sa.Column("institution", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("balance_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "personal_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("personal_accounts.id"), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False, server_default="general"),
        sa.Column("description", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transaction_kind", sa.String(length=20), nullable=False, server_default="expense"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "savings_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("target_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(length=24), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    for c in ["tenant_id", "name"]:
        op.create_index(_idx("personal_accounts", c), "personal_accounts", [c])

    for c in ["tenant_id", "account_id", "transaction_date", "category", "transaction_kind"]:
        op.create_index(_idx("personal_transactions", c), "personal_transactions", [c])

    for c in ["tenant_id", "title", "target_date"]:
        op.create_index(_idx("savings_goals", c), "savings_goals", [c])


def downgrade() -> None:
    for c in ["tenant_id", "title", "target_date"]:
        op.drop_index(_idx("savings_goals", c), table_name="savings_goals")

    for c in ["tenant_id", "account_id", "transaction_date", "category", "transaction_kind"]:
        op.drop_index(_idx("personal_transactions", c), table_name="personal_transactions")

    for c in ["tenant_id", "name"]:
        op.drop_index(_idx("personal_accounts", c), table_name="personal_accounts")

    op.drop_table("savings_goals")
    op.drop_table("personal_transactions")
    op.drop_table("personal_accounts")
