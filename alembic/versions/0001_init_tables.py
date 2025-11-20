"""create trades and orderbook_snapshots tables

Revision ID: 0001_init_tables
Revises: 
Create Date: 2025-11-14
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_init_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String, nullable=False, index=True),
        sa.Column("instrument", sa.String, nullable=False, index=True),
        sa.Column("trade_id", sa.String, nullable=True, index=True),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("size", sa.Float, nullable=False),
        sa.Column("side", sa.String, nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "orderbook_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String, nullable=False, index=True),
        sa.Column("instrument", sa.String, nullable=False, index=True),
        sa.Column("sequence", sa.Integer, nullable=True),
        sa.Column("bids", sa.JSON, nullable=False),
        sa.Column("asks", sa.JSON, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("orderbook_snapshots")
    op.drop_table("trades")