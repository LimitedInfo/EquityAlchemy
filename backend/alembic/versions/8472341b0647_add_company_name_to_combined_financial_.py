"""add company_name to combined_financial_statements

Revision ID: 8472341b0647
Revises: bf8c043bf4dd
Create Date: 2025-07-20 11:34:38.537392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# gitleaks:disable
revision: str = '8472341b0647' #pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = 'bf8c043bf4dd' #pragma: allowlist secret
# gitleaks:enable
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Skip if column already exists (for databases where table was created with column)
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Skip downgrade
    pass
