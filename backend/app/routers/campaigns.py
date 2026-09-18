from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Campaign, CampaignRun
from ..schemas import CampaignCreate, CampaignOut, CampaignUpdate, LaunchRequest, RunDetail, RunOut
from ..services.audience import resolve_audience
from ..services.bedrock import nova_client
from ..services.engine import cancel_run, start_run

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)) -> list[Campaign]:
    return list(db.scalars(select(Campaign).order_by(Campaign.id.desc())))


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)) -> Campaign:
    data = payload.model_dump()
    data["audience_filter"] = payload.audience_filter.model_dump()
    data["model_id"] = payload.model_id or get_settings().bedrock_model_id
    campaign = Campaign(**data)
    db.add(campaign)
    db.commit()
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, payload: CampaignUpdate, db: Session = Depends(get_db)) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "audience_filter" and value is not None:
            campaign.audience_filter = dict(value)
        elif value is not None:
            setattr(campaign, field, value)
    db.commit()
    return campaign


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)) -> None:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    db.delete(campaign)
    db.commit()


@router.post("/{campaign_id}/launch", response_model=RunOut, status_code=202)
def launch_campaign(campaign_id: int, payload: LaunchRequest, db: Session = Depends(get_db)) -> CampaignRun:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    audience = resolve_audience(db, campaign.audience_filter)
    if not audience:
        raise HTTPException(400, "Audience is empty for this campaign filter")

    run = CampaignRun(
        campaign_id=campaign.id,
        status="queued",
        audience_size=len(audience),
        llm_provider=nova_client.provider,
    )
    db.add(run)
    campaign.status = "running"
    db.commit()

    start_run(run.id, payload.simulate_engagement, payload.delay_ms)
    return run


@router.get("/{campaign_id}/runs", response_model=list[RunOut])
def list_runs(campaign_id: int, db: Session = Depends(get_db)) -> list[CampaignRun]:
    return list(
        db.scalars(select(CampaignRun).where(CampaignRun.campaign_id == campaign_id).order_by(CampaignRun.id.desc()))
    )


runs_router = APIRouter(prefix="/api/runs", tags=["runs"])


@runs_router.get("", response_model=list[RunOut])
def all_runs(db: Session = Depends(get_db), limit: int = 25) -> list[CampaignRun]:
    return list(db.scalars(select(CampaignRun).order_by(CampaignRun.id.desc()).limit(limit)))


@runs_router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: int, db: Session = Depends(get_db)) -> CampaignRun:
    run = db.get(CampaignRun, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run


@runs_router.post("/{run_id}/cancel", status_code=202)
def cancel(run_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    if db.get(CampaignRun, run_id) is None:
        raise HTTPException(404, "Run not found")
    return {"cancelled": cancel_run(run_id)}
