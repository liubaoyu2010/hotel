from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def uuid_str() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="manager")
    hotel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hotel_lat: Mapped[str] = mapped_column(String(32), nullable=False)
    hotel_lng: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    competitors: Mapped[list["CompetitorHotel"]] = relationship(back_populates="user")


class CompetitorHotel(Base):
    __tablename__ = "competitor_hotels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="meituan")
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    room_types: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="competitors")
    prices: Mapped[list["PriceTimeSeries"]] = relationship(back_populates="competitor")


class PriceTimeSeries(Base):
    __tablename__ = "price_time_series"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    competitor_hotel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("competitor_hotels.id"), nullable=False
    )
    room_type: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    availability: Mapped[bool | None] = mapped_column(Boolean)
    data_source: Mapped[str] = mapped_column(String(20), default="extension")
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    competitor: Mapped[CompetitorHotel] = relationship(back_populates="prices")


class ExtensionDevice(Base):
    __tablename__ = "extension_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    extension_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="offline")
    version: Mapped[str | None] = mapped_column(String(20))
    last_collect_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SurroundingActivity(Base):
    __tablename__ = "surrounding_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    demand_level: Mapped[str] = mapped_column(String(20), nullable=False)
    demand_score: Mapped[float | None] = mapped_column(Numeric(3, 2))
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, default="price_drop")
    threshold: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=15.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertRecord(Base):
    __tablename__ = "alert_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    alert_rule_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("alert_rules.id"))
    competitor_hotel_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("competitor_hotels.id")
    )
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CompetitorAlias(Base):
    __tablename__ = "competitor_aliases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AIReport(Base):
    __tablename__ = "ai_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False, default="weekly")
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PushDelivery(Base):
    __tablename__ = "push_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="console")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
