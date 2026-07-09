"""Unit tests for scripts/facts/compiler.py."""
import pytest

from scripts.facts.models import (
    Claim,
    DraftFacts,
    TownEventsResult,
    ValidationResult,
    VerifiedClaim,
    WeatherFacts,
)
from scripts.facts.compiler import compile_facts, format_weather_str


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _claim(text: str, ctype: str = "landmark") -> Claim:
    return Claim(type=ctype, text=text)


def _vc(text: str, source: str = "AT location database", conf: float = 1.0) -> VerifiedClaim:
    return VerifiedClaim(claim=_claim(text), source=source, confidence=conf)


def _weather(high=55.0, low=32.0, cond="Partly cloudy") -> WeatherFacts:
    return WeatherFacts(
        high_f=high,
        low_f=low,
        precip_in=0.1,
        conditions=cond,
        source="Open-Meteo archive",
        coords=(34.5, -84.2),
    )


def _draft(summary="Test section.", claims=None) -> DraftFacts:
    return DraftFacts(
        trail_section_summary=summary,
        claims=claims or [],
        at_mile_start=None,
        at_mile_end=8.1,
        state="Georgia",
        nearest_town=None,
    )


def _meta():
    return {
        "date": "2010-02-07",
        "destination": "Hawk Mountain Shelter",
        "start_location": "Hike Inn",
        "miles_hiked": 9.0,
        "total_miles": 9.0,
    }


# ---------------------------------------------------------------------------
# format_weather_str
# ---------------------------------------------------------------------------

class TestFormatWeatherStr:
    def test_full_weather(self):
        w = _weather(55.0, 32.0, "Partly cloudy")
        s = format_weather_str(w)
        assert "55" in s
        assert "32" in s
        assert "Partly cloudy" in s

    def test_high_only(self):
        w = WeatherFacts(high_f=60.0, low_f=None, precip_in=None,
                         conditions=None, source="test", coords=None)
        s = format_weather_str(w)
        assert "60" in s
        assert "low" not in s.lower()

    def test_low_only(self):
        w = WeatherFacts(high_f=None, low_f=28.0, precip_in=None,
                         conditions=None, source="test", coords=None)
        s = format_weather_str(w)
        assert "28" in s

    def test_none_weather(self):
        assert format_weather_str(None) == ""

    def test_no_temps_returns_empty(self):
        w = WeatherFacts(high_f=None, low_f=None, precip_in=None,
                         conditions="Sunny", source="test", coords=None)
        assert format_weather_str(w) == ""

    def test_conditions_period_not_doubled(self):
        w = WeatherFacts(high_f=50.0, low_f=30.0, precip_in=None,
                         conditions="Clear sky.", source="test", coords=None)
        s = format_weather_str(w)
        assert ".." not in s


# ---------------------------------------------------------------------------
# compile_facts — confidence levels
# ---------------------------------------------------------------------------

class TestCompileFactsConfidence:
    def test_high_confidence_two_verified_plus_weather(self):
        validation = ValidationResult(
            verified=[_vc("Claim A"), _vc("Claim B")],
            rejected=[],
            corrections=[],
        )
        compiled = compile_facts(validation, _weather(), TownEventsResult(), _meta())
        assert compiled.confidence >= 0.8

    def test_medium_confidence_weather_only(self):
        validation = ValidationResult(verified=[], rejected=[], corrections=[])
        compiled = compile_facts(validation, _weather(), TownEventsResult(), _meta())
        assert 0.3 <= compiled.confidence < 0.8

    def test_low_confidence_no_weather_no_verified(self):
        validation = ValidationResult(verified=[], rejected=[], corrections=[])
        compiled = compile_facts(validation, None, TownEventsResult(), _meta())
        assert compiled.confidence < 0.3

    def test_one_verified_plus_weather_medium_not_high(self):
        validation = ValidationResult(
            verified=[_vc("Single claim")],
            rejected=[],
            corrections=[],
        )
        compiled = compile_facts(validation, _weather(), TownEventsResult(), _meta())
        # One verified claim is < 2, so not high confidence
        assert compiled.confidence < 0.8


# ---------------------------------------------------------------------------
# compile_facts — output structure
# ---------------------------------------------------------------------------

class TestCompileFactsOutput:
    def test_weather_stored_when_present(self):
        validation = ValidationResult(verified=[], rejected=[], corrections=[])
        compiled = compile_facts(validation, _weather(), TownEventsResult(), _meta())
        assert compiled.weather is not None
        assert compiled.weather.high_f == 55.0

    def test_weather_none_when_absent(self):
        validation = ValidationResult(verified=[], rejected=[], corrections=[])
        compiled = compile_facts(validation, None, TownEventsResult(), _meta())
        assert compiled.weather is None

    def test_weather_none_when_no_temps(self):
        w = WeatherFacts(high_f=None, low_f=None, precip_in=None,
                         conditions="Sunny", source="test", coords=None)
        validation = ValidationResult(verified=[], rejected=[], corrections=[])
        compiled = compile_facts(validation, w, TownEventsResult(), _meta())
        assert compiled.weather is None

    def test_trail_section_populated_from_draft(self):
        claims = [_claim("Claim 1"), _claim("Claim 2")]
        draft = _draft(claims=claims)
        validation = ValidationResult(
            verified=[_vc("Claim 1"), _vc("Claim 2")],
            rejected=[],
            corrections=[],
        )
        compiled = compile_facts(validation, _weather(), TownEventsResult(), _meta(), draft)
        assert compiled.trail_section is not None
        assert len(compiled.trail_section.claims) == 2
        assert compiled.trail_section.state == "Georgia"

    def test_trail_section_filters_to_verified_only(self):
        c1, c2, c3 = _claim("Keep"), _claim("Keep too"), _claim("Reject")
        draft = _draft(claims=[c1, c2, c3])
        validation = ValidationResult(
            verified=[_vc("Keep"), _vc("Keep too")],
            rejected=[c3],
            corrections=[],
        )
        compiled = compile_facts(validation, _weather(), TownEventsResult(), _meta(), draft)
        texts = [c.text for c in compiled.trail_section.claims]
        assert "Keep" in texts
        assert "Keep too" in texts
        assert "Reject" not in texts

    def test_sources_collected(self):
        validation = ValidationResult(
            verified=[_vc("Claim", source="AT location database")],
            rejected=[],
            corrections=[],
        )
        compiled = compile_facts(validation, _weather(), TownEventsResult(), _meta())
        assert "AT location database" in compiled.sources
        assert "Open-Meteo archive" in compiled.sources

    def test_sources_deduplicated(self):
        validation = ValidationResult(
            verified=[
                _vc("C1", source="AT location database"),
                _vc("C2", source="AT location database"),
            ],
            rejected=[],
            corrections=[],
        )
        compiled = compile_facts(validation, _weather(), TownEventsResult(), _meta())
        assert compiled.sources.count("AT location database") == 1

    def test_town_events_stored(self):
        te = TownEventsResult(event="Trail Days festival", source="web", confidence=0.8)
        validation = ValidationResult(verified=[], rejected=[], corrections=[])
        compiled = compile_facts(validation, None, te, _meta())
        assert compiled.town_events is not None
        assert compiled.town_events.event == "Trail Days festival"

    def test_no_draft_reconstructs_from_verified(self):
        validation = ValidationResult(
            verified=[_vc("Lone claim")],
            rejected=[],
            corrections=[],
        )
        compiled = compile_facts(validation, None, TownEventsResult(), _meta())
        assert compiled.trail_section is not None
        assert compiled.trail_section.claims[0].text == "Lone claim"
