"""add_balance_sheet_data_to_combined_financial_statements

Revision ID: c12f34a5b678
Revises: 57d8fcda632a
Create Date: 2025-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# gitleaks:disable
revision: str = 'c12f34a5b678' #pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = '57d8fcda632a' #pragma: allowlist secret
# gitleaks:enable
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        json_type = sa.dialects.postgresql.JSONB
    else:
        json_type = sa.Text

    op.add_column(
        'combined_financial_statements',
        sa.Column('balance_sheet_data', json_type(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('combined_financial_statements', 'balance_sheet_data')


