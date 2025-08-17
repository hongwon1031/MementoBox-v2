"""update story_year(DateTime to Integer) column from photos table

Revision ID: 63e90841254a
Revises: 714032500010
Create Date: 2025-06-08 16:36:21.634455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '63e90841254a'
down_revision: Union[str, None] = '714032500010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # DateTime -> Integer (연도만 추출)
    op.alter_column(
        'photos',
        'story_year',
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="EXTRACT(YEAR FROM story_year)::integer"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Integer -> DateTime (해당 연도의 1월 1일 0시 0분 0초로 변환)
    op.alter_column(
        'photos',
        'story_year',
        existing_type=sa.Integer(),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
        postgresql_using="make_timestamp(story_year, 1, 1, 0, 0, 0)"
    )
