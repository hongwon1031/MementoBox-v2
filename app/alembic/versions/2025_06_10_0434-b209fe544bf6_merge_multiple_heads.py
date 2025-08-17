"""merge multiple heads

Revision ID: b209fe544bf6
Revises: 893ceed3178c, 63e90841254a
Create Date: 2025-06-10 04:34:51.402416+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b209fe544bf6'
down_revision: Union[str, None] = ('893ceed3178c', '63e90841254a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
