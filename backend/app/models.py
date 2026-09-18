from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    phone: Mapped[str] = mapped_column(String(32))
    city: Mapped[str] = mapped_column(String(80))
    segment: Mapped[str] = mapped_column(String(40), index=True)
    risk_profile: Mapped[str] = mapped_column(String(20))
    annual_income: Mapped[float] = mapped_column(Float)
    relationship_years: Mapped[float] = mapped_column(Float, default=0)
    products_held: Mapped[list[str]] = mapped_column(JSON, default=list)
    kyc_status: Mapped[str] = mapped_column(String(20), default="verified")
    credit_score: Mapped[int] = mapped_column(Integer, default=700)
    preferred_channel: Mapped[str] = mapped_column(String(20), default="email")
    preferred_language: Mapped[str] = mapped_column(String(20), default="English")
    marketing_consent: Mapped[bool] = mapped_column(default=True)
    churn_risk: Mapped[float] = mapped_column(Float, default=0.2)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(140))
    objective: Mapped[str] = mapped_column(String(60))
    product: Mapped[str] = mapped_column(String(80))
    channel: Mapped[str] = mapped_column(String(20))
    tone: Mapped[str] = mapped_column(String(40), default="professional")
    language: Mapped[str] = mapped_column(String(30), default="English")
    offer_details: Mapped[str] = mapped_column(Text, default="")
    call_to_action: Mapped[str] = mapped_column(String(160), default="Apply now")
    audience_filter: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    model_id: Mapped[str] = mapped_column(String(80), default="amazon.nova-lite-v1:0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    runs: Mapped[list["CampaignRun"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", order_by="CampaignRun.id.desc()"
    )


class CampaignRun(Base):
    __tablename__ = "campaign_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    audience_size: Mapped[int] = mapped_column(Integer, default=0)
    generated: Mapped[int] = mapped_column(Integer, default=0)
    sent: Mapped[int] = mapped_column(Integer, default=0)
    blocked: Mapped[int] = mapped_column(Integer, default=0)
    opened: Mapped[int] = mapped_column(Integer, default=0)
    clicked: Mapped[int] = mapped_column(Integer, default=0)
    converted: Mapped[int] = mapped_column(Integer, default=0)
    llm_provider: Mapped[str] = mapped_column(String(30), default="bedrock")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    campaign: Mapped[Campaign] = relationship(back_populates="runs")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("campaign_runs.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    next_best_action: Mapped[str] = mapped_column(String(200), default="")
    compliance_status: Mapped[str] = mapped_column(String(20), default="pass", index=True)
    compliance_notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="generated", index=True)
    propensity: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[CampaignRun] = relationship(back_populates="messages")
    customer: Mapped[Customer] = relationship()
