"""Accounts: users, workspaces, memberships, login sessions and auth attempts."""
from alembic import op
import sqlalchemy as sa
revision='0009_auth'
down_revision='0008_wordpress'
branch_labels=None
depends_on=None

ROLE = sa.Enum('owner', 'member', name='workspace_role')
KIND = sa.Enum('login', 'register', name='auth_attempt_kind')


def _timestamps():
    return [sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]


def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(320), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('email_verified_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        *_timestamps())
    op.create_table('workspaces',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        *_timestamps())
    op.create_table('workspace_members',
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role', ROLE, nullable=False),
        *_timestamps())
    op.create_index('ix_workspace_members_user_id', 'workspace_members', ['user_id'])
    op.create_table('user_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('ip', sa.String(64)))
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_expires_at', 'user_sessions', ['expires_at'])
    op.create_table('auth_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('kind', KIND, nullable=False),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('ip', sa.String(64)),
        sa.Column('succeeded', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_auth_attempts_email_created', 'auth_attempts', ['email', 'created_at'])
    op.create_index('ix_auth_attempts_ip_kind_created', 'auth_attempts', ['ip', 'kind', 'created_at'])


def downgrade():
    for table in ('auth_attempts', 'user_sessions', 'workspace_members', 'workspaces', 'users'):
        op.drop_table(table)
    ROLE.drop(op.get_bind(), checkfirst=True)
    KIND.drop(op.get_bind(), checkfirst=True)
