from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Customer


def resolve_audience(db: Session, audience_filter: dict[str, Any] | None) -> list[Customer]:
    f = audience_filter or {}
    stmt = select(Customer)

    if f.get("segments"):
        stmt = stmt.where(Customer.segment.in_(f["segments"]))
    if f.get("cities"):
        stmt = stmt.where(Customer.city.in_(f["cities"]))
    if f.get("risk_profiles"):
        stmt = stmt.where(Customer.risk_profile.in_(f["risk_profiles"]))
    if f.get("min_income") is not None:
        stmt = stmt.where(Customer.annual_income >= f["min_income"])
    if f.get("max_income") is not None:
        stmt = stmt.where(Customer.annual_income <= f["max_income"])
    if f.get("min_credit_score") is not None:
        stmt = stmt.where(Customer.credit_score >= f["min_credit_score"])
    if f.get("kyc_status"):
        stmt = stmt.where(Customer.kyc_status == f["kyc_status"])
    if f.get("consent_required", True):
        stmt = stmt.where(Customer.marketing_consent.is_(True))

    customers = list(db.scalars(stmt.order_by(Customer.churn_risk.desc(), Customer.id)))

    excluded = {p.lower() for p in f.get("exclude_products", [])}
    if excluded:
        customers = [c for c in customers if not excluded & {p.lower() for p in (c.products_held or [])}]

    limit = int(f.get("limit") or 25)
    return customers[:limit]
