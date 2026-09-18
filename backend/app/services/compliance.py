"""Deterministic BFSI compliance guardrails applied to every generated message."""

from __future__ import annotations

import re
from dataclasses import dataclass

CHANNEL_LIMITS = {
    "sms": 320,
    "whatsapp": 600,
    "push": 140,
    "email": 2000,
    "social": 400,
    "print": 1200,
}

DISCLAIMER_REQUIRED_CHANNELS = {"email", "whatsapp", "social", "print"}

BANNED_PATTERNS: list[tuple[str, str]] = [
    (r"\bguarantee(d|s)?\b", "Guarantee language is not permitted for financial products"),
    (r"\bassured\s+(returns?|profit)\b", "Assured return claim"),
    (r"\brisk[- ]free\b", "Risk-free claim"),
    (r"\bno\s+risk\b", "No-risk claim"),
    (r"\bdouble\s+your\s+money\b", "Unrealistic return claim"),
    (r"\b100%\s+(safe|secure|approval)\b", "Absolute safety/approval claim"),
    (r"\binstant\s+approval\b", "Approval cannot be promised before underwriting"),
]

PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "PAN number present in copy"),
    (r"\b\d{4}\s?\d{4}\s?\d{4}\b", "Aadhaar/card-like number present in copy"),
    (r"\bcredit score\s*(is|of)?\s*\d{3}\b", "Credit score disclosed"),
]

DISCLAIMER_HINTS = (
    "t&c",
    "terms and conditions",
    "terms apply",
    "terms & conditions",
    "subject to",
    "risk",
    "disclaimer",
)


@dataclass
class ComplianceResult:
    status: str  # pass | warn | fail
    notes: str

    @property
    def blocked(self) -> bool:
        return self.status == "fail"


def check(body: str, channel: str, offer_details: str = "") -> ComplianceResult:
    issues: list[str] = []
    warnings: list[str] = []
    text = body or ""
    lowered = text.lower()

    for pattern, reason in BANNED_PATTERNS:
        if re.search(pattern, lowered):
            issues.append(reason)
    for pattern, reason in PII_PATTERNS:
        if re.search(pattern, text):
            issues.append(reason)

    limit = CHANNEL_LIMITS.get(channel, 2000)
    if len(text) > limit:
        issues.append(f"Exceeds {channel} length limit ({len(text)}/{limit} chars)")

    quoted_rates = set(re.findall(r"\d+(?:\.\d+)?\s?%", text))
    allowed_rates = set(re.findall(r"\d+(?:\.\d+)?\s?%", offer_details or ""))
    unsupported = quoted_rates - allowed_rates
    if unsupported:
        issues.append(f"Unsupported rate claim: {', '.join(sorted(unsupported))}")

    if channel in DISCLAIMER_REQUIRED_CHANNELS and not any(hint in lowered for hint in DISCLAIMER_HINTS):
        warnings.append("Missing risk/T&C disclaimer")
    if not text.strip():
        issues.append("Empty message body")

    if issues:
        return ComplianceResult("fail", "; ".join(issues))
    if warnings:
        return ComplianceResult("warn", "; ".join(warnings))
    return ComplianceResult("pass", "All guardrails satisfied")
