"""client website and social handle fields

Revision ID: 0008_client_web_social_fields
Revises: 0007_marketing_module
Create Date: 2026-02-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_client_web_social_fields"
down_revision = "0007_marketing_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("website_url", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("clients", sa.Column("social_handles", sa.String(length=255), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("clients", "social_handles")
    op.drop_column("clients", "website_url")

