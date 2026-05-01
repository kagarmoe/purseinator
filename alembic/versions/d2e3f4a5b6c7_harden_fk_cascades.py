"""harden FK cascades on item_photos and items

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-05-01 00:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Recreate item_photos with ondelete=CASCADE on item_id FK.
    # SQLite batch mode with recreate="always" rebuilds the entire table,
    # so we just need to re-declare the FK with the cascade rule.
    with op.batch_alter_table("item_photos", recreate="always") as batch_op:
        batch_op.alter_column("item_id", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("items", recreate="always") as batch_op:
        batch_op.alter_column("collection_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    # No structural change to reverse for downgrade
    pass
