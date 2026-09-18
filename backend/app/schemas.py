from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Channel = Literal["email", "sms", "whatsapp", "push"]


class CustomerBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str = ""
    city: str = ""
    segment: str = "mass"
    risk_profile: str = "moderate"
    annual_income: float = 0
    relationship_years: float = 0
    products_held: list[str] = Field(default_factory=list)
    kyc_status: str = "verified"
    credit_score: int = 700
    preferred_channel: Channel = "email"
    preferred_language: str = "English"
    marketing_consent: bool = True
    churn_risk: float = 0.2


class CustomerCreate(CustomerBase):
    pass


class CustomerOut(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class AudienceFilter(BaseModel):
    segments: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    risk_profiles: list[str] = Field(default_factory=list)
    min_income: float | None = None
    max_income: float | None = None
    min_credit_score: int | None = None
    exclude_products: list[str] = Field(default_factory=list)
    kyc_status: str | None = "verified"
    consent_required: bool = True
    limit: int = 25


class CampaignBase(BaseModel):
    name: str
    objective: str = "cross_sell"
    product: str
    channel: Channel = "email"
    tone: str = "professional"
    language: str = "English"
    offer_details: str = ""
    call_to_action: str = "Apply now"
    audience_filter: AudienceFilter = Field(default_factory=AudienceFilter)
    model_id: str | None = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    product: str | None = None
    channel: Channel | None = None
    tone: str | None = None
    language: str | None = None
    offer_details: str | None = None
    call_to_action: str | None = None
    audience_filter: AudienceFilter | None = None
    status: str | None = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    objective: str
    product: str
    channel: str
    tone: str
    language: str
    offer_details: str
    call_to_action: str
    audience_filter: dict[str, Any]
    status: str
    model_id: str
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    run_id: int
    customer_id: int
    channel: str
    subject: str
    body: str
    next_best_action: str
    compliance_status: str
    compliance_notes: str
    status: str
    propensity: float
    latency_ms: int
    input_tokens: int
    output_tokens: int
    created_at: datetime


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    campaign_id: int
    status: str
    audience_size: int
    generated: int
    sent: int
    blocked: int
    opened: int
    clicked: int
    converted: int
    llm_provider: str
    error: str | None
    started_at: datetime
    finished_at: datetime | None


class RunDetail(RunOut):
    messages: list[MessageOut] = Field(default_factory=list)


class LaunchRequest(BaseModel):
    simulate_engagement: bool = True
    delay_ms: int = 350


class AnalyticsOut(BaseModel):
    total_campaigns: int
    active_runs: int
    audience_reached: int
    messages_generated: int
    blocked_by_compliance: int
    open_rate: float
    click_rate: float
    conversion_rate: float
    avg_latency_ms: float
    by_channel: dict[str, int]
    by_segment: dict[str, int]
