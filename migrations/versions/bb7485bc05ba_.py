"""empty message

Revision ID: bb7485bc05ba
Revises: 1fa2b55f58bb
Create Date: 2017-07-06 13:40:17.930680

"""

# revision identifiers, used by Alembic.
revision = 'bb7485bc05ba'
down_revision = '1fa2b55f58bb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('variables')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('variables',
    sa.Column('id', sa.VARCHAR(length=32), autoincrement=False, nullable=False),
    sa.Column('key', sa.VARCHAR(length=512), autoincrement=False, nullable=True),
    sa.Column('value', sa.VARCHAR(length=512), autoincrement=False, nullable=True),
    sa.Column('readonly', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('t', sa.VARCHAR(length=16), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=u'pk_variables'),
    sa.UniqueConstraint('key', name=u'uq_variables_key')
    )
    ### end Alembic commands ###
