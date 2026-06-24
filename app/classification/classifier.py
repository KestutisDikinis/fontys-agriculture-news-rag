from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import re


RUMOR = "rumor"
UPCOMING_THIS_MONTH = "upcoming_this_month"
UPCOMING_WITHIN_YEAR = "upcoming_within_year"
CURRENT_OR_RECENT = "current_or_recent"
BACKGROUND_NEWS = "background_news"

RUMOR_TERMS = {
    "rumor",
    "rumour",
    "unconfirmed",
    "sources say",
    "could",
    "may",
    "expected",
    "proposal",
    "proposed",
    "draft",
    "consultation",
    "plans to",
    "considering",
    "set to",
}

LAW_TERMS = {
    "law",
    "legislation",
    "regulation",
    "directive",
    "rule",
    "act",
    "policy",
    "scheme",
    "subsidy",
    "grant",
    "compliance",
    "inspection",
    "ban",
    "licence",
    "license",
    "deadline",
    "tariff",
    "tax",
    "pesticide",
    "fertiliser",
    "fertilizer",
}

HIGH_IMPACT_TERMS = {
    "ban",
    "mandatory",
    "penalty",
    "fine",
    "subsidy",
    "grant",
    "tax",
    "tariff",
    "inspection",
    "compliance",
    "pesticide",
    "fertiliser",
    "fertilizer",
}

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    confidence: float
    effective_date: date | None = None
    impact_level: str = "medium"
    reasons: tuple[str, ...] = ()


def _today(now: datetime | None = None) -> date:
    if now is None:
        now = datetime.now(timezone.utc)
    return now.date()


def _normalise_text(*parts: str | None) -> str:
    return " ".join(p for p in parts if p).lower()


def _parse_date_candidate(raw: str, today: date) -> date | None:
    raw = raw.strip().replace(",", "")

    # 2026-03-15
    match = re.fullmatch(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if match:
        year, month, day = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    # 15/03/2026 or 15-03-2026
    match = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})[-/](20\d{2})", raw)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    # 15 March 2026, March 15 2026, March 2026, 15 March
    tokens = raw.lower().split()
    if not tokens:
        return None

    month = None
    year = None
    day = 1
    for token in tokens:
        if token in MONTHS:
            month = MONTHS[token]
        elif token.isdigit() and len(token) == 4:
            year = int(token)
        elif token.isdigit() and 1 <= int(token) <= 31:
            day = int(token)

    if month is None:
        return None
    if year is None:
        year = today.year

    try:
        candidate = date(year, month, day)
    except ValueError:
        return None

    # If no year was supplied and date already passed, assume next year.
    if str(year) not in raw and candidate < today:
        try:
            candidate = date(today.year + 1, month, day)
        except ValueError:
            return None
    return candidate


def extract_effective_date(text: str, now: datetime | None = None) -> date | None:
    """Extract a likely law/effective/deadline date from article text."""
    today = _today(now)
    lowered = text.lower()

    relative_patterns = {
        "next month": _first_day_next_month(today),
        "this month": today,
        "next year": date(today.year + 1, 1, 1),
    }
    for phrase, candidate in relative_patterns.items():
        if phrase in lowered:
            return candidate

    date_patterns = [
        r"(?:effective|from|applies from|takes effect|starts on|deadline(?: is)?|by|before)\s+([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})",
        r"(?:effective|from|applies from|takes effect|starts on|deadline(?: is)?|by|before)\s+([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{4})",
        r"(?:effective|from|applies from|takes effect|starts on|deadline(?: is)?|by|before)\s+(\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+20\d{2})?)",
        r"(?:effective|from|applies from|takes effect|starts on|deadline(?: is)?|by|before)\s+((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:\s+20\d{2})?)",
        r"(?:effective|from|applies from|takes effect|starts on|deadline(?: is)?|by|before)\s+((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+20\d{2})",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, lowered)
        if match:
            parsed = _parse_date_candidate(match.group(1), today)
            if parsed:
                return parsed

    # Fallback: parse any explicit date in the next 365 days.
    generic = re.search(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]20\d{2})\b", lowered)
    if generic:
        return _parse_date_candidate(generic.group(1), today)

    return None


def _first_day_next_month(today: date) -> date:
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


def _is_same_month(a: date, b: date) -> bool:
    return a.year == b.year and a.month == b.month


def classify_text(
    title: str,
    summary: str = "",
    content: str = "",
    now: datetime | None = None,
) -> ClassificationResult:
    """Classify an agricultural article into the buckets farmers care about."""
    text = _normalise_text(title, summary, content)
    today = _today(now)
    effective_date = extract_effective_date(text, now=now)

    reasons: list[str] = []
    score = 0.55

    has_rumor_terms = any(term in text for term in RUMOR_TERMS)
    has_law_terms = any(term in text for term in LAW_TERMS)

    if has_law_terms:
        reasons.append("contains law/policy/compliance terms")
        score += 0.1

    if has_rumor_terms:
        reasons.append("contains proposal/rumor/uncertain wording")
        category = RUMOR
        score += 0.2
    elif effective_date and _is_same_month(effective_date, today):
        reasons.append("effective date is this month")
        category = UPCOMING_THIS_MONTH
        score += 0.25
    elif effective_date and today < effective_date <= today + timedelta(days=365):
        reasons.append("effective date is within the next year")
        category = UPCOMING_WITHIN_YEAR
        score += 0.2
    elif has_law_terms:
        reasons.append("law/policy item without a future effective date")
        category = CURRENT_OR_RECENT
    else:
        reasons.append("general agriculture news")
        category = BACKGROUND_NEWS
        score -= 0.1

    impact = "high" if any(term in text for term in HIGH_IMPACT_TERMS) else "medium"
    if impact == "high":
        score += 0.05
        reasons.append("contains high-impact farming terms")

    return ClassificationResult(
        category=category,
        confidence=round(max(0.05, min(score, 0.98)), 2),
        effective_date=effective_date,
        impact_level=impact,
        reasons=tuple(reasons),
    )
