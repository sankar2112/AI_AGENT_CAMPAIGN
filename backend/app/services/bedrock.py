"""Amazon Bedrock Nova client for BFSI campaign copy generation.

Uses the Bedrock Runtime `converse` API. When AWS credentials are not available
and `allow_mock_llm` is enabled, a deterministic local generator is used so the
whole pipeline stays runnable offline.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from ..config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a marketing copywriter for a regulated BFSI (banking, financial services and insurance) institution.
Write hyper-personalised, factual outreach for a single customer.

Hard rules:
- Never promise guaranteed returns, assured profit, risk-free investment or approval.
- Never state an interest rate, fee or eligibility figure that is not present in the offer details.
- Always keep the customer's data confidential: no account numbers, no credit scores, no income figures in the copy.
- Include a short risk/T&C disclaimer suited to the product.
- Respect the channel format and limits:
  - email: subject line plus <= 200 words, greeting and sign-off.
  - sms: <= 320 characters, plain text, no links unless given in the offer details.
  - whatsapp: <= 600 characters, short paragraphs, conversational.
  - push: <= 140 characters, one sentence, no disclaimer needed.
  - social: <= 400 characters of ad/post copy, no direct personal data, broad appeal with a hook.
  - print: <= 1200 characters of branch leaflet or letter copy, formal register, printable layout with a headline then body.

Reply with JSON only, matching exactly:
{"subject": str, "body": str, "next_best_action": str, "propensity": float between 0 and 1}"""


@dataclass
class Generation:
    subject: str
    body: str
    next_best_action: str
    propensity: float
    latency_ms: int
    input_tokens: int
    output_tokens: int
    provider: str


class BedrockNovaClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Any | None = None
        self._available: bool | None = None

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.settings.aws_region,
                config=Config(retries={"max_attempts": 3, "mode": "standard"}, read_timeout=60),
            )
        return self._client

    def available(self) -> bool:
        if self._available is None:
            try:
                self._available = boto3.Session().get_credentials() is not None
            except (BotoCoreError, NoCredentialsError):
                self._available = False
        return bool(self._available)

    @property
    def provider(self) -> str:
        return "bedrock" if self.available() else "mock"

    def generate(self, prompt: str, model_id: str | None = None, context: dict[str, Any] | None = None) -> Generation:
        started = time.perf_counter()
        model = model_id or self.settings.bedrock_model_id
        if not self.available():
            if not self.settings.allow_mock_llm:
                raise RuntimeError("AWS credentials unavailable and mock LLM is disabled")
            gen = _mock_generation(context or {})
            gen.latency_ms = int((time.perf_counter() - started) * 1000)
            return gen

        response = self.client.converse(
            modelId=model,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                "maxTokens": self.settings.bedrock_max_tokens,
                "temperature": self.settings.bedrock_temperature,
                "topP": 0.9,
            },
        )
        text = "".join(block.get("text", "") for block in response["output"]["message"]["content"])
        usage = response.get("usage", {})
        payload = _parse_json(text)
        return Generation(
            subject=str(payload.get("subject", ""))[:200],
            body=str(payload.get("body", text)).strip(),
            next_best_action=str(payload.get("next_best_action", ""))[:200],
            propensity=_clamp(payload.get("propensity", 0.5)),
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=int(usage.get("inputTokens", 0)),
            output_tokens=int(usage.get("outputTokens", 0)),
            provider="bedrock",
        )

    def review_compliance(self, body: str, model_id: str | None = None) -> dict[str, Any]:
        """Optional LLM-as-reviewer pass; rule engine remains the source of truth."""
        if not self.available():
            return {"verdict": "skipped", "notes": ""}
        try:
            response = self.client.converse(
                modelId=model_id or self.settings.bedrock_model_id,
                system=[
                    {
                        "text": "You are a BFSI compliance reviewer. Reply JSON only: "
                        '{"verdict": "pass"|"warn"|"fail", "notes": str}'
                    }
                ],
                messages=[{"role": "user", "content": [{"text": body}]}],
                inferenceConfig={"maxTokens": 200, "temperature": 0.0},
            )
            text = "".join(b.get("text", "") for b in response["output"]["message"]["content"])
            return _parse_json(text)
        except (ClientError, BotoCoreError, KeyError, ValueError) as exc:  # pragma: no cover - network path
            logger.warning("compliance review failed: %s", exc)
            return {"verdict": "skipped", "notes": str(exc)}


def _clamp(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.S)
        if brace:
            text = brace.group(0)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"subject": "", "body": text, "next_best_action": "", "propensity": 0.5}
    return parsed if isinstance(parsed, dict) else {"body": text}


_MOCK_OPENERS = [
    "Hi {name}, thanks for banking with us for {years} years.",
    "Hello {name}, your {segment} relationship unlocks a new option.",
    "Dear {name}, here is something tailored to your {risk} profile.",
]


def _mock_generation(ctx: dict[str, Any]) -> Generation:
    rng = random.Random(f"{ctx.get('customer_id')}::{ctx.get('campaign_id')}")
    name = str(ctx.get("first_name", "there"))
    product = str(ctx.get("product", "our latest offering"))
    channel = str(ctx.get("channel", "email"))
    cta = str(ctx.get("call_to_action", "Apply now"))
    offer = str(ctx.get("offer_details", "")).strip()
    opener = rng.choice(_MOCK_OPENERS).format(
        name=name,
        years=ctx.get("relationship_years", 1),
        segment=ctx.get("segment", "valued"),
        risk=ctx.get("risk_profile", "balanced"),
    )
    disclaimer = "T&C apply. Products are subject to eligibility checks; market-linked products carry risk."
    if channel == "sms":
        body = f"{opener} {product} is now available for you. {cta}. {disclaimer}"[:320]
    elif channel == "push":
        body = f"{name}, {product} is ready for you. {cta}."[:140]
    elif channel == "whatsapp":
        body = f"{opener}\n\n{product}: {offer or 'personalised terms based on your relationship with us.'}\n{cta}\n{disclaimer}"[:600]
    elif channel == "social":
        body = (
            f"{product} — built for {ctx.get('segment', 'our')} customers who want more from their money. "
            f"{offer or 'Personalised terms, decided with you.'} {cta}. {disclaimer}"
        )[:400]
    elif channel == "print":
        body = (
            f"{product.upper()}\n\n"
            f"Dear {name},\n\n"
            f"{offer or 'We have reviewed your relationship with us and prepared personalised terms for you.'}\n\n"
            f"Visit your nearest branch or {cta.lower()} to speak with a relationship manager.\n\n"
            f"{disclaimer}"
        )[:1200]
    else:
        body = (
            f"{opener}\n\nBased on your current portfolio we think {product} fits your goals. "
            f"{offer or 'Terms are personalised to your profile.'}\n\n{cta} in the app, or reply to this email "
            f"and a relationship manager will call you back.\n\n{disclaimer}"
        )
    return Generation(
        subject=f"{name}, a personalised {product} option for you" if channel in {"email", "print"} else "",
        body=body,
        next_best_action=rng.choice(
            [
                "Schedule a relationship manager callback",
                "Send pre-approved offer link in app",
                "Follow up on WhatsApp in 3 days",
                "Invite to branch for portfolio review",
            ]
        ),
        propensity=round(rng.uniform(0.25, 0.9), 2),
        latency_ms=0,
        input_tokens=0,
        output_tokens=0,
        provider="mock",
    )


nova_client = BedrockNovaClient()
