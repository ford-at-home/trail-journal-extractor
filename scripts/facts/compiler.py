"""Deterministic facts compiler.

Assembles validated claims, weather data, and town events into CompiledFacts.
No LLM or external service calls are made here.

Confidence scale (float 0–1):
  high   ≥ 0.8 : 2+ verified claims AND weather present
  medium ≈ 0.5 : weather present but fewer than 2 verified claims
  low    ≈ 0.2 : neither condition met
"""
from typing import Optional

from scripts.facts.models import (
    CompiledFacts,
    DraftFacts,
    TownEventsResult,
    ValidationResult,
    WeatherFacts,
)

_CONFIDENCE_HIGH = 0.9
_CONFIDENCE_MEDIUM = 0.5
_CONFIDENCE_LOW = 0.2


def format_weather_str(weather: Optional[WeatherFacts]) -> str:
    """Format a WeatherFacts object into the canonical display string."""
    if not weather:
        return ""
    if weather.high_f is None and weather.low_f is None:
        return ""

    parts: list = []
    if weather.high_f is not None and weather.low_f is not None:
        parts.append(f"High {weather.high_f:.0f}°F, low {weather.low_f:.0f}°F.")
    elif weather.high_f is not None:
        parts.append(f"High {weather.high_f:.0f}°F.")
    elif weather.low_f is not None:
        parts.append(f"Low {weather.low_f:.0f}°F.")

    if weather.conditions:
        cond = weather.conditions.rstrip(".")
        parts.append(f"{cond}.")

    return " ".join(parts)


def _collect_sources(
    validation: ValidationResult,
    weather: Optional[WeatherFacts],
    town_events: Optional[TownEventsResult],
) -> list:
    sources: list = []
    seen: set = set()

    for vc in validation.verified:
        s = vc.source
        if s and s not in seen:
            sources.append(s)
            seen.add(s)

    if weather and weather.source and weather.source not in seen:
        sources.append(weather.source)
        seen.add(weather.source)

    if town_events and town_events.source and town_events.source not in seen:
        sources.append(town_events.source)
        seen.add(town_events.source)

    return sources


def compile_facts(
    validation: ValidationResult,
    weather: Optional[WeatherFacts],
    town_events: Optional[TownEventsResult],
    metadata,
    draft: Optional[DraftFacts] = None,
) -> CompiledFacts:
    """Assemble a CompiledFacts object from pipeline outputs.

    Args:
        validation:   result from validate_agent.validate_claims
        weather:      result from weather_agent.fetch_weather (may be None)
        town_events:  result from town_events_agent.fetch_town_events
        metadata:     dict or EntryMetadata with entry fields
        draft:        original DraftFacts (used to populate CompiledFacts.trail_section)
    """
    verified_count = len(validation.verified)
    has_weather = weather is not None and (
        weather.high_f is not None or weather.low_f is not None
    )

    if verified_count >= 2 and has_weather:
        confidence = _CONFIDENCE_HIGH
    elif has_weather:
        confidence = _CONFIDENCE_MEDIUM
    else:
        confidence = _CONFIDENCE_LOW

    # Build filtered DraftFacts from verified claims when draft is available
    trail_section: Optional[DraftFacts] = None
    if draft is not None:
        verified_claim_texts = {vc.claim.text for vc in validation.verified}
        filtered_claims = [c for c in draft.claims if c.text in verified_claim_texts]
        trail_section = DraftFacts(
            trail_section_summary=draft.trail_section_summary,
            claims=filtered_claims,
            at_mile_start=draft.at_mile_start,
            at_mile_end=draft.at_mile_end,
            state=draft.state,
            nearest_town=draft.nearest_town,
            segment_name=draft.segment_name,
            region=draft.region,
        )
    elif validation.verified:
        # Reconstruct minimal DraftFacts from verified claims alone
        trail_section = DraftFacts(
            trail_section_summary=" ".join(vc.claim.text for vc in validation.verified),
            claims=[vc.claim for vc in validation.verified],
            at_mile_start=None,
            at_mile_end=None,
            state=None,
            nearest_town=None,
        )

    sources = _collect_sources(validation, weather, town_events)

    return CompiledFacts(
        weather=weather if has_weather else None,
        trail_section=trail_section,
        town_events=town_events,
        confidence=confidence,
        sources=sources,
    )
