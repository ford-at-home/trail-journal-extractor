"""YAML frontmatter builder and injector for journal entries.

Produces Hugo/Jekyll-compatible YAML frontmatter from CompiledFacts.
Uses PyYAML (available via boto3's dependency chain) for serialisation.
"""
from typing import Optional

from scripts.facts.models import CompiledFacts, FrontmatterData
from scripts.facts.compiler import format_weather_str


def _get_attr(obj, attr: str, default=None):
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _to_frontmatter_data(metadata, compiled: CompiledFacts) -> FrontmatterData:
    """Map pipeline outputs to a FrontmatterData dataclass."""
    date = _get_attr(metadata, "date") or ""
    destination = _get_attr(metadata, "destination") or ""
    start_location = _get_attr(metadata, "start_location") or ""
    miles_hiked = float(_get_attr(metadata, "miles_hiked") or 0.0)
    total_miles = float(_get_attr(metadata, "total_miles") or 0.0)

    title = destination or date

    ts = compiled.trail_section
    state: Optional[str] = ts.state if ts else None
    nearest_town: Optional[str] = ts.nearest_town if ts else None
    at_mile_start: Optional[float] = ts.at_mile_start if ts else None
    at_mile_end: Optional[float] = ts.at_mile_end if ts else None
    trail_section_summary: Optional[str] = ts.trail_section_summary if ts else None

    weather = compiled.weather
    weather_high_f: Optional[float] = weather.high_f if weather else None
    weather_low_f: Optional[float] = weather.low_f if weather else None
    weather_precip_in: Optional[float] = weather.precip_in if weather else None
    weather_conditions: Optional[str] = weather.conditions if weather else None
    weather_source: Optional[str] = weather.source if weather else None
    weather_caveat: Optional[str] = weather.caveat if weather else None

    town_event: Optional[str] = (
        compiled.town_events.event
        if compiled.town_events and compiled.town_events.event
        else None
    )

    return FrontmatterData(
        date=date,
        title=title,
        start_location=start_location,
        destination=destination,
        miles_hiked=miles_hiked,
        total_miles=total_miles,
        state=state,
        nearest_town=nearest_town,
        at_mile_start=at_mile_start,
        at_mile_end=at_mile_end,
        weather_high_f=weather_high_f,
        weather_low_f=weather_low_f,
        weather_precip_in=weather_precip_in,
        weather_conditions=weather_conditions,
        weather_source=weather_source,
        weather_caveat=weather_caveat,
        trail_section_summary=trail_section_summary,
        town_event=town_event,
    )


def _frontmatter_data_to_dict(fm: FrontmatterData) -> dict:
    """Convert FrontmatterData to an ordered dict, omitting None values."""
    import dataclasses

    raw = dataclasses.asdict(fm)

    # Preferred key ordering for readability
    ordered_keys = [
        "date", "title", "start_location", "destination",
        "miles_hiked", "total_miles",
        "state", "nearest_town",
        "at_mile_start", "at_mile_end",
        "weather_high_f", "weather_low_f", "weather_precip_in",
        "weather_conditions", "weather_source", "weather_caveat",
        "trail_section_summary",
        "town_event",
    ]
    result: dict = {}
    for key in ordered_keys:
        val = raw.get(key)
        if val is not None:
            result[key] = val
    # Include any extra fields not in the ordered list
    for key, val in raw.items():
        if key not in result and val is not None:
            result[key] = val
    return result


def _confidence_label(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _trail_section_text(compiled: CompiledFacts) -> Optional[str]:
    ts = compiled.trail_section
    if not ts:
        return None
    if ts.claims:
        return " ".join(c.text for c in ts.claims)
    return ts.trail_section_summary or None


def build_frontmatter(metadata, compiled: CompiledFacts) -> str:
    """Return a YAML frontmatter block (including --- delimiters) for an entry."""
    import yaml

    date = _get_attr(metadata, "date") or ""
    start_location = _get_attr(metadata, "start_location") or ""
    destination = _get_attr(metadata, "destination") or ""
    miles_hiked = float(_get_attr(metadata, "miles_hiked") or 0.0)
    total_miles = float(_get_attr(metadata, "total_miles") or 0.0)

    weather_summary = format_weather_str(compiled.weather) or None
    trail_section = _trail_section_text(compiled)
    town_events = None
    if compiled.town_events and compiled.town_events.event:
        town_events = compiled.town_events.event

    data_dict = {
        "date": date,
        "start": start_location,
        "destination": destination,
        "miles_today": miles_hiked,
        "trip_miles": total_miles,
        "facts": {
            "weather": weather_summary,
            "trail_section": trail_section,
            "town_events": town_events,
            "confidence": _confidence_label(compiled.confidence),
            "sources": compiled.sources or None,
        },
    }

    # Drop empty facts keys
    facts = data_dict["facts"]
    data_dict["facts"] = {k: v for k, v in facts.items() if v is not None}

    yaml_str = yaml.safe_dump(
        data_dict,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return f"---\n{yaml_str}---\n"


def inject_frontmatter(entry_text: str, frontmatter: str) -> str:
    """Prepend frontmatter immediately before the first # header line.

    If no header is found, the frontmatter is prepended to the entry.
    Leading blank lines before the header are preserved.
    """
    lines = entry_text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("#"):
            prefix = "\n".join(lines[:i])
            rest = "\n".join(lines[i:])
            if prefix:
                return prefix + "\n" + frontmatter + rest
            return frontmatter + rest
    # No header found — prepend
    return frontmatter + entry_text


def has_frontmatter(entry_text: str) -> bool:
    """Return True if the entry already starts with a YAML frontmatter block."""
    stripped = entry_text.lstrip()
    if not stripped.startswith("---"):
        return False
    # Must have a closing --- on a subsequent line
    after_open = stripped[3:].lstrip("\n")
    return "---" in after_open
