"""'Schema' column added for validating 'value' column (JSON)

Revision ID: 545dfafaa2a8
Revises: bb7485bc05ba
Create Date: 2017-07-27 08:08:53.961692

"""

# revision identifiers, used by Alembic.
revision = '545dfafaa2a8'
down_revision = 'bb7485bc05ba'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # commands auto generated by Alembic - please adjust! ###
    op.add_column('namespaced_keyvalues', sa.Column('_schema', sa.Text(), nullable=True))
    # end Alembic commands ###


def downgrade():
    # commands auto generated by Alembic - please adjust! ###
    op.drop_column('namespaced_keyvalues', '_schema')
    # end Alembic commands ###
