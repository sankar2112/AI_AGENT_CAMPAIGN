"""Seed the BFSI campaign database with a realistic demo book of customers."""

from __future__ import annotations

import random

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Campaign, Customer

FIRST_NAMES = [
    "Aarav", "Diya", "Rohan", "Meera", "Kabir", "Ananya", "Vikram", "Sneha", "Arjun", "Priya",
    "Nikhil", "Isha", "Rahul", "Kavya", "Siddharth", "Nandini", "Aditya", "Pooja", "Manav", "Tara",
    "Farhan", "Lakshmi", "Dev", "Ritika", "Harsh", "Sanjana", "Varun", "Neha", "Karthik", "Shreya",
]
LAST_NAMES = ["Sharma", "Iyer", "Nair", "Patel", "Reddy", "Menon", "Kulkarni", "Banerjee", "Singh", "Rao"]
CITIES = ["Mumbai", "Chennai", "Bengaluru", "Hyderabad", "Pune", "Delhi", "Kochi", "Ahmedabad"]
SEGMENTS = ["mass", "affluent", "hni", "nri", "sme"]
RISK = ["conservative", "moderate", "aggressive"]
PRODUCTS = [
    "savings_account", "credit_card", "home_loan", "personal_loan", "auto_loan",
    "term_insurance", "health_insurance", "mutual_fund_sip", "fixed_deposit", "demat_account",
]
CHANNELS = ["email", "sms", "whatsapp", "push"]


def seed_customers(count: int = 120) -> int:
    rng = random.Random(42)
    db = SessionLocal()
    try:
        if db.scalar(select(Customer).limit(1)):
            print("customers already present, skipping")
            return 0
        for i in range(count):
            first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
            segment = rng.choices(SEGMENTS, weights=[45, 25, 10, 8, 12])[0]
            income = {
                "mass": rng.uniform(300_000, 900_000),
                "affluent": rng.uniform(1_200_000, 3_500_000),
                "hni": rng.uniform(4_000_000, 20_000_000),
                "nri": rng.uniform(2_000_000, 9_000_000),
                "sme": rng.uniform(1_500_000, 8_000_000),
            }[segment]
            db.add(
                Customer(
                    full_name=f"{first} {last}",
                    email=f"{first.lower()}.{last.lower()}{i}@example.com",
                    phone=f"+91{rng.randint(7000000000, 9999999999)}",
                    city=rng.choice(CITIES),
                    segment=segment,
                    risk_profile=rng.choice(RISK),
                    annual_income=round(income, 2),
                    relationship_years=round(rng.uniform(0.5, 18), 1),
                    products_held=rng.sample(PRODUCTS, rng.randint(1, 4)),
                    kyc_status=rng.choices(["verified", "pending"], weights=[92, 8])[0],
                    credit_score=rng.randint(580, 840),
                    preferred_channel=rng.choice(CHANNELS),
                    preferred_language=rng.choice(["English", "Hindi", "Tamil", "Telugu", "Marathi"]),
                    marketing_consent=rng.random() > 0.08,
                    churn_risk=round(rng.uniform(0.02, 0.85), 2),
                )
            )
        db.commit()
        return count
    finally:
        db.close()


DEMO_CAMPAIGNS = [
    dict(
        name="HNI Wealth Portfolio Review Q3",
        objective="cross_sell",
        product="Managed Wealth Portfolio",
        channel="email",
        tone="consultative",
        offer_details="Zero advisory fee for the first 6 months; minimum investment 10 lakh.",
        call_to_action="Book a portfolio review",
        audience_filter=dict(segments=["hni", "affluent"], kyc_status="verified", consent_required=True, limit=12),
    ),
    dict(
        name="Pre-approved Credit Card Upgrade",
        objective="upsell",
        product="Platinum Rewards Credit Card",
        channel="whatsapp",
        tone="friendly",
        offer_details="Lifetime free for existing customers; 5X reward points on fuel and groceries.",
        call_to_action="Activate in the app",
        audience_filter=dict(
            segments=["mass", "affluent"], min_credit_score=720, exclude_products=["credit_card"], limit=10
        ),
    ),
    dict(
        name="Term Insurance Protection Drive",
        objective="acquisition",
        product="Term Life Insurance Plan",
        channel="sms",
        tone="reassuring",
        offer_details="Cover up to 1 crore; premiums start from 700 per month for eligible applicants.",
        call_to_action="Check your premium",
        audience_filter=dict(exclude_products=["term_insurance"], min_income=500_000, limit=10),
    ),
]


def seed_campaigns() -> int:
    db = SessionLocal()
    try:
        if db.scalar(select(Campaign).limit(1)):
            print("campaigns already present, skipping")
            return 0
        for payload in DEMO_CAMPAIGNS:
            db.add(Campaign(**payload))
        db.commit()
        return len(DEMO_CAMPAIGNS)
    finally:
        db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print(f"seeded customers: {seed_customers()}")
    print(f"seeded campaigns: {seed_campaigns()}")
