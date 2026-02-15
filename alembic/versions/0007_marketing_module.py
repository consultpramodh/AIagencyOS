"""marketing module tables

Revision ID: 0007_marketing_module
Revises: 0006_phase2_intelligence
Create Date: 2026-02-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_marketing_module"
down_revision = "0006_phase2_intelligence"
branch_labels = None
depends_on = None


def _idx(table: str, col: str) -> None:
    op.create_index(op.f(f"ix_{table}_{col}"), table, [col], unique=False)


def upgrade() -> None:
    op.create_table(
        "marketing_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("platform", sa.String(length=60), nullable=False),
        sa.Column("objective", sa.String(length=60), nullable=False),
        sa.Column("budget_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("existing_keywords_json", sa.String(), nullable=False, server_default="[]"),
        sa.Column("plan_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for c in ["tenant_id", "client_id", "name", "platform", "objective"]:
        _idx("marketing_campaigns", c)

    op.create_table(
        "marketing_keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(length=160), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for c in ["tenant_id", "campaign_id", "keyword"]:
        _idx("marketing_keywords", c)


def downgrade() -> None:
    op.drop_table("marketing_keywords")
    op.drop_table("marketing_campaigns")

