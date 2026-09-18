from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Campaign, CampaignRun, Customer, Message
from ..schemas import AnalyticsOut

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _rate(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


@router.get("/overview", response_model=AnalyticsOut)
def overview(db: Session = Depends(get_db)) -> AnalyticsOut:
    totals = db.execute(
        select(
            func.coalesce(func.sum(CampaignRun.audience_size), 0),
            func.coalesce(func.sum(CampaignRun.generated), 0),
            func.coalesce(func.sum(CampaignRun.sent), 0),
            func.coalesce(func.sum(CampaignRun.blocked), 0),
            func.coalesce(func.sum(CampaignRun.opened), 0),
            func.coalesce(func.sum(CampaignRun.clicked), 0),
            func.coalesce(func.sum(CampaignRun.converted), 0),
        )
    ).one()
    audience, generated, sent, blocked, opened, clicked, converted = (int(v) for v in totals)

    by_channel = {
        channel: int(count)
        for channel, count in db.execute(select(Message.channel, func.count()).group_by(Message.channel)).all()
    }
    by_segment = {
        segment: int(count)
        for segment, count in db.execute(
            select(Customer.segment, func.count(Message.id)).join(Message, Message.customer_id == Customer.id).group_by(Customer.segment)
        ).all()
    }

    return AnalyticsOut(
        total_campaigns=int(db.scalar(select(func.count(Campaign.id))) or 0),
        active_runs=int(db.scalar(select(func.count(CampaignRun.id)).where(CampaignRun.status == "running")) or 0),
        audience_reached=audience,
        messages_generated=generated,
        blocked_by_compliance=blocked,
        open_rate=_rate(opened, sent),
        click_rate=_rate(clicked, sent),
        conversion_rate=_rate(converted, sent),
        avg_latency_ms=round(float(db.scalar(select(func.avg(Message.latency_ms))) or 0), 1),
        by_channel=by_channel,
        by_segment=by_segment,
    )
