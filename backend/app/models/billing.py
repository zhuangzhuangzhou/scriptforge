import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class BillingRecord(Base):
    """账单记录表"""

    __tablename__ = "billing_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 账单类型: recharge(充值), consume(消费), refund(退款), subscription(订阅)
    type = Column(String(50), nullable=False, index=True)

    # 金额(分)
    amount = Column(Integer, default=0)

    # 积分变动
    credits = Column(Integer, default=0)

    # 变动后余额
    balance_after = Column(Integer)

    # 描述
    description = Column(String(500))

    # 关联ID(订单号等)
    reference_id = Column(String(100), index=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class Subscription(Base):
    """订阅记录表"""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 订阅等级: creator(创作者版), studio(工作室版), enterprise(企业版)
    tier = Column(String(20), nullable=False, index=True)

    # 订阅状态: active(生效中), expired(已过期), cancelled(已取消)
    status = Column(String(20), nullable=False, default="active", index=True)

    # 订阅金额(分)
    amount = Column(Integer, default=0)

    # 订阅开始时间
    started_at = Column(TIMESTAMP(timezone=True), nullable=False)

    # 订阅过期时间
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
