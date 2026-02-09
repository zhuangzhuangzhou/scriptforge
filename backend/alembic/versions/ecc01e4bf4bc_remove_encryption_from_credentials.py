"""remove encryption from credentials

Revision ID: ecc01e4bf4bc
Revises: eece6c8e3bad
Create Date: 2026-02-08 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ecc01e4bf4bc'
down_revision = 'eece6c8e3bad'
branch_labels = None
depends_on = None


def upgrade():
    """
    移除加密功能：
    1. 将 api_key_encrypted 重命名为 api_key
    2. 将 api_secret_encrypted 重命名为 api_secret

    ⚠️ 警告：此迁移会导致现有加密数据无法使用！
    如果数据库中已有加密的凭证，需要先解密后再运行此迁移。
    """
    # 重命名列
    op.alter_column('ai_model_credentials', 'api_key_encrypted',
                    new_column_name='api_key',
                    existing_type=sa.Text(),
                    existing_nullable=False)

    op.alter_column('ai_model_credentials', 'api_secret_encrypted',
                    new_column_name='api_secret',
                    existing_type=sa.Text(),
                    existing_nullable=True)


def downgrade():
    """
    恢复加密功能：
    1. 将 api_key 重命名为 api_key_encrypted
    2. 将 api_secret 重命名为 api_secret_encrypted
    """
    # 重命名列
    op.alter_column('ai_model_credentials', 'api_key',
                    new_column_name='api_key_encrypted',
                    existing_type=sa.Text(),
                    existing_nullable=False)

    op.alter_column('ai_model_credentials', 'api_secret',
                    new_column_name='api_secret_encrypted',
                    existing_type=sa.Text(),
                    existing_nullable=True)
