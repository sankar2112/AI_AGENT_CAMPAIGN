"""Campaign execution engine: audience resolution -> Nova generation -> compliance -> delivery.

Every state transition is published to the event hub so the React UI can render
the run in real time.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Campaign, CampaignRun, Customer, Message
from . import compliance
from .audience import resolve_audience
from .bedrock import nova_client
from .events import hub

logger = logging.getLogger(__name__)

_running: dict[int, asyncio.Task[None]] = {}
_loop: asyncio.AbstractEventLoop | None = None


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Register the server event loop so sync request handlers can schedule runs."""
    global _loop
    _loop = loop


def build_prompt(campaign: Campaign, customer: Customer) -> str:
    products = ", ".join(customer.products_held or []) or "none"
    return f"""Campaign brief
- Objective: {campaign.objective}
- Product to promote: {campaign.product}
- Channel: {campaign.channel}
- Tone: {campaign.tone}
- Language: {campaign.language}
- Offer details (the ONLY facts/figures you may quote): {campaign.offer_details or 'no specific figures provided'}
- Call to action: {campaign.call_to_action}

Customer profile (context only - never repeat sensitive values back)
- First name: {customer.full_name.split()[0]}
- Segment: {customer.segment}
- City: {customer.city}
- Risk profile: {customer.risk_profile}
- Relationship tenure: {customer.relationship_years} years
- Products already held: {products}
- Preferred language: {customer.preferred_language}
- Churn risk: {customer.churn_risk}

Write the outreach for this customer and estimate their propensity to act."""


def _context(campaign: Campaign, customer: Customer) -> dict[str, Any]:
    return {
        "campaign_id": campaign.id,
        "customer_id": customer.id,
        "first_name": customer.full_name.split()[0],
        "product": campaign.product,
        "channel": campaign.channel,
        "call_to_action": campaign.call_to_action,
        "offer_details": campaign.offer_details,
        "segment": customer.segment,
        "risk_profile": customer.risk_profile,
        "relationship_years": customer.relationship_years,
    }


def _engagement(propensity: float, rng: random.Random) -> tuple[bool, bool, bool]:
    opened = rng.random() < min(0.95, 0.35 + propensity * 0.5)
    clicked = opened and rng.random() < min(0.9, propensity * 0.6)
    converted = clicked and rng.random() < min(0.8, propensity * 0.35)
    return opened, clicked, converted


async def _emit(event_type: str, run_id: int, campaign_id: int, **payload: Any) -> None:
    await hub.publish(
        {
            "type": event_type,
            "run_id": run_id,
            "campaign_id": campaign_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
    )


def _generate_sync(campaign: Campaign, customer: Customer) -> Any:
    return nova_client.generate(
        build_prompt(campaign, customer),
        model_id=campaign.model_id,
        context=_context(campaign, customer),
    )


async def execute_run(run_id: int, simulate_engagement: bool = True, delay_ms: int = 350) -> None:
    db: Session = SessionLocal()
    rng = random.Random(run_id)
    try:
        run = db.get(CampaignRun, run_id)
        if run is None:
            return
        campaign = db.get(Campaign, run.campaign_id)
        if campaign is None:
            return

        audience = resolve_audience(db, campaign.audience_filter)
        run.audience_size = len(audience)
        run.status = "running"
        run.llm_provider = nova_client.provider
        campaign.status = "running"
        db.commit()

        await _emit(
            "run_started",
            run.id,
            campaign.id,
            campaign_name=campaign.name,
            audience_size=run.audience_size,
            llm_provider=run.llm_provider,
        )

        for index, customer in enumerate(audience, start=1):
            generation = await asyncio.to_thread(_generate_sync, campaign, customer)
            verdict = compliance.check(generation.body, campaign.channel, campaign.offer_details)

            message = Message(
                run_id=run.id,
                customer_id=customer.id,
                channel=campaign.channel,
                subject=generation.subject,
                body=generation.body,
                next_best_action=generation.next_best_action,
                compliance_status=verdict.status,
                compliance_notes=verdict.notes,
                status="blocked" if verdict.blocked else "sent",
                propensity=generation.propensity,
                latency_ms=generation.latency_ms,
                input_tokens=generation.input_tokens,
                output_tokens=generation.output_tokens,
            )
            db.add(message)
            run.generated += 1
            if verdict.blocked:
                run.blocked += 1
            else:
                run.sent += 1
                if simulate_engagement:
                    opened, clicked, converted = _engagement(generation.propensity, rng)
                    run.opened += int(opened)
                    run.clicked += int(clicked)
                    run.converted += int(converted)
                    if converted:
                        message.status = "converted"
                    elif clicked:
                        message.status = "clicked"
                    elif opened:
                        message.status = "opened"
            db.commit()

            await _emit(
                "message",
                run.id,
                campaign.id,
                index=index,
                total=run.audience_size,
                message={
                    "id": message.id,
                    "customer_id": customer.id,
                    "customer_name": customer.full_name,
                    "segment": customer.segment,
                    "channel": message.channel,
                    "subject": message.subject,
                    "body": message.body,
                    "next_best_action": message.next_best_action,
                    "compliance_status": message.compliance_status,
                    "compliance_notes": message.compliance_notes,
                    "status": message.status,
                    "propensity": message.propensity,
                    "latency_ms": message.latency_ms,
                },
                stats=_stats(run),
            )
            if delay_ms:
                await asyncio.sleep(delay_ms / 1000)

        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        campaign.status = "completed"
        db.commit()
        await _emit("run_completed", run.id, campaign.id, stats=_stats(run))
    except asyncio.CancelledError:
        _mark_failed(db, run_id, "Run cancelled")
        raise
    except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
        logger.exception("campaign run %s failed", run_id)
        campaign_id = _mark_failed(db, run_id, str(exc))
        await _emit("run_failed", run_id, campaign_id or 0, error=str(exc))
    finally:
        _running.pop(run_id, None)
        db.close()


def _mark_failed(db: Session, run_id: int, error: str) -> int | None:
    run = db.get(CampaignRun, run_id)
    if run is None:
        return None
    run.status = "failed"
    run.error = error
    run.finished_at = datetime.now(timezone.utc)
    campaign = db.get(Campaign, run.campaign_id)
    if campaign is not None:
        campaign.status = "failed"
    db.commit()
    return run.campaign_id


def _stats(run: CampaignRun) -> dict[str, int]:
    return {
        "audience_size": run.audience_size,
        "generated": run.generated,
        "sent": run.sent,
        "blocked": run.blocked,
        "opened": run.opened,
        "clicked": run.clicked,
        "converted": run.converted,
    }


def start_run(run_id: int, simulate_engagement: bool = True, delay_ms: int = 350) -> None:
    if run_id in _running:
        return
    coro = execute_run(run_id, simulate_engagement, delay_ms)
    try:
        _running[run_id] = asyncio.get_running_loop().create_task(coro)
        return
    except RuntimeError:
        pass
    if _loop is None:
        raise RuntimeError("event loop is not bound; campaign runs cannot be scheduled")
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    _running[run_id] = future  # type: ignore[assignment]


def cancel_run(run_id: int) -> bool:
    task = _running.get(run_id)
    if task is None:
        return False
    task.cancel()
    return True
