"""client contact fields

Revision ID: 0004_client_contact_fields
Revises: 0003_service_scheduler_calendar
Create Date: 2026-02-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_client_contact_fields"
down_revision = "0003_service_scheduler_calendar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("contact_name", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("clients", sa.Column("contact_email", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("clients", sa.Column("contact_phone", sa.String(length=40), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("clients", "contact_phone")
    op.drop_column("clients", "contact_email")
    op.drop_column("clients", "contact_name")
