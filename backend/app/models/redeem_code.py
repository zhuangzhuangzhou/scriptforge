"""兑换码模型"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class RedeemCode(Base):
    """兑换码表"""

    __tablename__ = "redeem_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 兑换码（唯一，用于用户输入）
    code = Column(String(32), unique=True, index=True, nullable=False)

    # 兑换类型: credits(积分充值) / tier_upgrade(等级升级)
    type = Column(String(20), nullable=False, default="credits")

    # 积分数量（type=credits 时有效）
    credits = Column(Integer, default=0)

    # 升级到的等级（type=tier_upgrade 时有效）
    tier = Column(String(20), nullable=True)

    # 升级有效天数（type=tier_upgrade 时有效）
    tier_days = Column(Integer, default=30)

    # 最大使用次数（0 表示无限制）
    max_uses = Column(Integer, default=1)

    # 已使用次数
    used_count = Column(Integer, default=0)

    # 是否启用
    is_active = Column(Boolean, default=True)

    # 过期时间（NULL 表示永不过期）
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # 备注
    note = Column(String(500), nullable=True)

    # 创建者（管理员）
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class RedeemRecord(Base):
    """兑换记录表"""

    __tablename__ = "redeem_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 关联兑换码
    redeem_code_id = Column(UUID(as_uuid=True), ForeignKey("redeem_codes.id", ondelete="CASCADE"), nullable=False, index=True)

    # 兑换用户
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 兑换时的码值（冗余存储，方便查询）
    code = Column(String(32), nullable=False)

    # 兑换类型
    type = Column(String(20), nullable=False)

    # 兑换获得的积分
    credits_granted = Column(Integer, default=0)

    # 兑换前后的等级（如果是升级）
    tier_before = Column(String(20), nullable=True)
    tier_after = Column(String(20), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
