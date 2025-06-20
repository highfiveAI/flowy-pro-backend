"""create table

Revision ID: facc52c53631
Revises: c171e2354d7d
Create Date: 2025-06-10 09:42:06.669498

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'facc52c53631'
down_revision: Union[str, None] = 'c171e2354d7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_table('langchain_pg_collection')
    # op.drop_table('langchain_pg_embedding')
    op.drop_column('feedbacktype', 'feedback_detail')
    op.drop_column('meeting', 'meeting_audio_type')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('meeting', sa.Column('meeting_audio_type', sa.VARCHAR(length=30), autoincrement=False, nullable=False))
    op.add_column('feedbacktype', sa.Column('feedback_detail', sa.TEXT(), autoincrement=False, nullable=False))
    # op.create_table('langchain_pg_embedding',
    # sa.Column('collection_id', sa.UUID(), autoincrement=False, nullable=True),
    # sa.Column('embedding', Vector(None), autoincrement=False, nullable=True),
    # sa.Column('document', sa.VARCHAR(), autoincrement=False, nullable=True),
    # sa.Column('cmetadata', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    # sa.Column('custom_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    # sa.Column('uuid', sa.UUID(), autoincrement=False, nullable=False),
    # sa.ForeignKeyConstraint(['collection_id'], ['langchain_pg_collection.uuid'], name=op.f('langchain_pg_embedding_collection_id_fkey'), ondelete='CASCADE'),
    # sa.PrimaryKeyConstraint('uuid', name=op.f('langchain_pg_embedding_pkey'))
    # )
    # op.create_table('langchain_pg_collection',
    # sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=True),
    # sa.Column('cmetadata', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    # sa.Column('uuid', sa.UUID(), autoincrement=False, nullable=False),
    # sa.PrimaryKeyConstraint('uuid', name=op.f('langchain_pg_collection_pkey'))
    # )
    # ### end Alembic commands ###
