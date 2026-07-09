"""Unit tests for scripts/facts/frontmatter.py."""
import pytest
import yaml

from scripts.facts.models import (
    Claim,
    CompiledFacts,
    DraftFacts,
    TownEventsResult,
    WeatherFacts,
)
from scripts.facts.frontmatter import (
    build_frontmatter,
    has_frontmatter,
    inject_frontmatter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _weather() -> WeatherFacts:
    return WeatherFacts(
        high_f=55.0,
        low_f=32.0,
        precip_in=0.0,
        conditions="Partly cloudy",
        source="Open-Meteo archive",
        coords=(34.5, -84.2),
    )


def _draft() -> DraftFacts:
    return DraftFacts(
        trail_section_summary="From Hike Inn to Hawk Mountain through hardwood forest.",
        claims=[Claim("terrain", "Rocky ridgeline hiking through the Georgia Blue Ridge.")],
        at_mile_start=None,
        at_mile_end=8.1,
        state="Georgia",
        nearest_town=None,
    )


def _compiled(with_weather=True, with_draft=True) -> CompiledFacts:
    return CompiledFacts(
        weather=_weather() if with_weather else None,
        trail_section=_draft() if with_draft else None,
        town_events=TownEventsResult(event=None),
        confidence=0.9,
        sources=["AT location database", "Open-Meteo archive"],
    )


def _metadata():
    return {
        "date": "2010-02-07",
        "destination": "Hawk Mountain Shelter",
        "start_location": "Hike Inn",
        "miles_hiked": 9.0,
        "total_miles": 9.0,
    }


# ---------------------------------------------------------------------------
# has_frontmatter
# ---------------------------------------------------------------------------

class TestHasFrontmatter:
    def test_returns_true_for_valid_frontmatter(self):
        entry = "---\ndate: 2010-02-07\n---\n# Header"
        assert has_frontmatter(entry) is True

    def test_returns_false_for_plain_entry(self):
        entry = "# Thursday, February 07, 2010 — Hawk Mountain Shelter\nBody"
        assert has_frontmatter(entry) is False

    def test_returns_false_for_empty_string(self):
        assert has_frontmatter("") is False

    def test_leading_whitespace_handled(self):
        entry = "\n---\ndate: 2010-02-07\n---\n# Header"
        assert has_frontmatter(entry) is True

    def test_single_dash_line_not_frontmatter(self):
        entry = "-\n# Header"
        assert has_frontmatter(entry) is False


# ---------------------------------------------------------------------------
# build_frontmatter
# ---------------------------------------------------------------------------

class TestBuildFrontmatter:
    def test_starts_and_ends_with_delimiters(self):
        fm = build_frontmatter(_metadata(), _compiled())
        assert fm.startswith("---\n")
        assert fm.rstrip("\n").endswith("---")

    def test_contains_date(self):
        fm = build_frontmatter(_metadata(), _compiled())
        assert "2010-02-07" in fm

    def test_contains_destination(self):
        fm = build_frontmatter(_metadata(), _compiled())
        assert "Hawk Mountain Shelter" in fm

    def test_contains_start_location(self):
        fm = build_frontmatter(_metadata(), _compiled())
        assert "Hike Inn" in fm

    def test_contains_weather_fields(self):
        fm = build_frontmatter(_metadata(), _compiled(with_weather=True))
        assert "55" in fm
        assert "32" in fm

    def test_weather_summary_string(self):
        fm = build_frontmatter(_metadata(), _compiled(with_weather=True))
        assert "Partly cloudy" in fm

    def test_omits_none_values(self):
        fm = build_frontmatter(_metadata(), _compiled(with_weather=False, with_draft=False))
        # Should not contain explicit 'null' or 'None' for omitted optional fields
        assert "null" not in fm
        assert ": None" not in fm

    def test_valid_yaml(self):
        fm = build_frontmatter(_metadata(), _compiled())
        inner = fm.strip().lstrip("-").split("---")[0].strip()
        parsed = yaml.safe_load(inner)
        assert isinstance(parsed, dict)

    def test_roundtrip_date_parseable(self):
        fm = build_frontmatter(_metadata(), _compiled())
        inner = fm.strip().lstrip("-").split("---")[0].strip()
        parsed = yaml.safe_load(inner)
        assert str(parsed.get("date", "")).startswith("2010")

    def test_confidence_present(self):
        fm = build_frontmatter(_metadata(), _compiled())
        assert "confidence:" in fm
        assert "facts:" in fm

    def test_trail_section_in_facts(self):
        fm = build_frontmatter(_metadata(), _compiled(with_draft=True))
        assert "trail_section:" in fm
        assert "Georgia" in fm or "hardwood" in fm.lower()


# ---------------------------------------------------------------------------
# inject_frontmatter
# ---------------------------------------------------------------------------

class TestInjectFrontmatter:
    _fm = "---\ndate: 2010-02-07\n---\n"
    _entry = "# Thursday, February 07, 2010 — Hawk Mountain Shelter\n**Start Location:** Hike Inn\n\nBody text."

    def test_result_starts_with_frontmatter(self):
        result = inject_frontmatter(self._entry, self._fm)
        assert result.startswith("---\n")

    def test_header_appears_after_frontmatter(self):
        result = inject_frontmatter(self._entry, self._fm)
        assert result.index("# Thursday") > result.index("---")

    def test_body_preserved(self):
        result = inject_frontmatter(self._entry, self._fm)
        assert "Body text." in result

    def test_header_preserved(self):
        result = inject_frontmatter(self._entry, self._fm)
        assert "# Thursday, February 07, 2010" in result

    def test_no_header_entry_prepended(self):
        entry = "Just plain text without a header."
        result = inject_frontmatter(entry, self._fm)
        assert result.startswith("---\n")
        assert "Just plain text" in result

    def test_has_frontmatter_true_after_inject(self):
        result = inject_frontmatter(self._entry, self._fm)
        assert has_frontmatter(result)

    def test_inject_idempotent_structure(self):
        """Injecting into an entry without frontmatter produces one --- block at start."""
        result = inject_frontmatter(self._entry, self._fm)
        assert result.count("---") >= 2


# ---------------------------------------------------------------------------
# build + inject roundtrip
# ---------------------------------------------------------------------------

class TestRoundtrip:
    def test_full_roundtrip(self):
        meta = _metadata()
        compiled = _compiled()
        fm = build_frontmatter(meta, compiled)
        entry = "# Thursday, February 07, 2010 — Hawk Mountain Shelter\n\nSome journal text."
        result = inject_frontmatter(entry, fm)

        assert has_frontmatter(result)
        assert "# Thursday" in result
        assert "journal text" in result

    def test_parsed_yaml_has_expected_keys(self):
        fm = build_frontmatter(_metadata(), _compiled())
        inner = fm.strip().lstrip("-").split("---")[0].strip()
        parsed = yaml.safe_load(inner)
        for key in ("date", "destination", "start", "miles_today", "facts"):
            assert key in parsed, f"Missing key: {key}"
