"""service scheduler and calendar

Revision ID: 0003_service_scheduler_calendar
Revises: 0002_m2_notes_tasks_attachments
Create Date: 2026-02-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_service_scheduler_calendar"
down_revision = "0002_m2_notes_tasks_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("service_type", sa.String(length=60), nullable=False),
        sa.Column("stage", sa.String(length=24), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_jobs_tenant_id"), "service_jobs", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_service_jobs_client_id"), "service_jobs", ["client_id"], unique=False)
    op.create_index(op.f("ix_service_jobs_project_id"), "service_jobs", ["project_id"], unique=False)
    op.create_index(op.f("ix_service_jobs_created_by_user_id"), "service_jobs", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_service_jobs_title"), "service_jobs", ["title"], unique=False)
    op.create_index(op.f("ix_service_jobs_stage"), "service_jobs", ["stage"], unique=False)
    op.create_index(op.f("ix_service_jobs_scheduled_for"), "service_jobs", ["scheduled_for"], unique=False)

    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_calendar_events_tenant_id"), "calendar_events", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_calendar_events_created_by_user_id"), "calendar_events", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_calendar_events_title"), "calendar_events", ["title"], unique=False)
    op.create_index(op.f("ix_calendar_events_event_date"), "calendar_events", ["event_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_calendar_events_event_date"), table_name="calendar_events")
    op.drop_index(op.f("ix_calendar_events_title"), table_name="calendar_events")
    op.drop_index(op.f("ix_calendar_events_created_by_user_id"), table_name="calendar_events")
    op.drop_index(op.f("ix_calendar_events_tenant_id"), table_name="calendar_events")
    op.drop_table("calendar_events")

    op.drop_index(op.f("ix_service_jobs_scheduled_for"), table_name="service_jobs")
    op.drop_index(op.f("ix_service_jobs_stage"), table_name="service_jobs")
    op.drop_index(op.f("ix_service_jobs_title"), table_name="service_jobs")
    op.drop_index(op.f("ix_service_jobs_created_by_user_id"), table_name="service_jobs")
    op.drop_index(op.f("ix_service_jobs_project_id"), table_name="service_jobs")
    op.drop_index(op.f("ix_service_jobs_client_id"), table_name="service_jobs")
    op.drop_index(op.f("ix_service_jobs_tenant_id"), table_name="service_jobs")
    op.drop_table("service_jobs")
