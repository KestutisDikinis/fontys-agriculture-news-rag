from datetime import datetime, timezone

from app.classification import (
    RUMOR,
    UPCOMING_THIS_MONTH,
    UPCOMING_WITHIN_YEAR,
    classify_text,
)

NOW = datetime(2026, 3, 5, tzinfo=timezone.utc)


def test_classifies_rumor_or_proposal():
    result = classify_text(
        "Draft pesticide regulation proposed",
        "The ministry is considering new pesticide limits.",
        now=NOW,
    )
    assert result.category == RUMOR


def test_classifies_upcoming_this_month():
    result = classify_text(
        "New fertiliser rule takes effect",
        "The regulation takes effect from 2026-03-20.",
        now=NOW,
    )
    assert result.category == UPCOMING_THIS_MONTH


def test_classifies_upcoming_within_year():
    result = classify_text(
        "Farm subsidy deadline announced",
        "Applications must be submitted before 2026-09-01.",
        now=NOW,
    )
    assert result.category == UPCOMING_WITHIN_YEAR
