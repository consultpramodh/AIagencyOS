"""phase2 dangerous intelligence data surfaces

Revision ID: 0006_phase2_intelligence
Revises: 0005_core_m3_to_m6
Create Date: 2026-02-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_phase2_intelligence"
down_revision = "0005_core_m3_to_m6"
branch_labels = None
depends_on = None


def _idx(table: str, col: str) -> None:
    op.create_index(op.f(f"ix_{table}_{col}"), table, [col], unique=False)


def upgrade() -> None:
    is_sqlite = op.get_bind().dialect.name == "sqlite"

    op.add_column("tasks", sa.Column("client_id", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(), nullable=True))
    if not is_sqlite:
        op.create_foreign_key("fk_tasks_client_id_clients", "tasks", "clients", ["client_id"], ["id"])
    _idx("tasks", "client_id")

    op.add_column("deals", sa.Column("close_date", sa.Date(), nullable=True))
    op.add_column("deals", sa.Column("probability_pct", sa.Integer(), nullable=False, server_default="0"))
    _idx("deals", "close_date")

    op.add_column("workflow_runs", sa.Column("client_id", sa.Integer(), nullable=True))
    op.add_column("workflow_runs", sa.Column("project_id", sa.Integer(), nullable=True))
    if not is_sqlite:
        op.create_foreign_key("fk_workflow_runs_client_id_clients", "workflow_runs", "clients", ["client_id"], ["id"])
        op.create_foreign_key("fk_workflow_runs_project_id_projects", "workflow_runs", "projects", ["project_id"], ["id"])
    _idx("workflow_runs", "client_id")
    _idx("workflow_runs", "project_id")

    op.create_table(
        "client_financials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("mrr_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retainer_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_invoice_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cogs_estimate_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for c in ["tenant_id", "client_id", "renewal_date"]:
        _idx("client_financials", c)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=60), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("detail_json", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for c in ["tenant_id", "type", "entity_type", "entity_id", "severity", "created_at"]:
        _idx("events", c)

    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("workflow_run_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for c in ["tenant_id", "client_id", "project_id", "workflow_run_id", "status", "requested_by_user_id", "created_at"]:
        _idx("approvals", c)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("before_json", sa.String(), nullable=False),
        sa.Column("after_json", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for c in ["tenant_id", "actor_user_id", "entity_type", "entity_id", "action", "created_at"]:
        _idx("audit_log", c)


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("approvals")
    op.drop_table("events")
    op.drop_table("client_financials")

    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_workflow_runs_project_id_projects", "workflow_runs", type_="foreignkey")
        op.drop_constraint("fk_workflow_runs_client_id_clients", "workflow_runs", type_="foreignkey")
    op.drop_column("workflow_runs", "project_id")
    op.drop_column("workflow_runs", "client_id")

    op.drop_column("deals", "probability_pct")
    op.drop_column("deals", "close_date")

    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_tasks_client_id_clients", "tasks", type_="foreignkey")
    op.drop_column("tasks", "completed_at")
    op.drop_column("tasks", "client_id")
