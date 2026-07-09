"""Pipeline orchestrator for journal frontmatter enrichment.

Public API:
    enrich_entry(metadata, entry_text, cache_dir, skip_firecrawl=True) -> str
    enrich_journal(input_path, output_path, cache_dir, limit=None, start=1)
"""
import dataclasses
import json
import re
from pathlib import Path
from typing import Optional

from scripts.facts.models import (
    Claim,
    CompiledFacts,
    DraftFacts,
    EntryMetadata,
    TownEventsResult,
    ValidationResult,
    VerifiedClaim,
    WeatherFacts,
)
from scripts.facts.cache import EntryCache
from scripts.facts.compiler import compile_facts
from scripts.facts.draft_agent import draft_section_facts
from scripts.facts.frontmatter import build_frontmatter, has_frontmatter, inject_frontmatter
from scripts.facts.town_events_agent import fetch_town_events
from scripts.facts.validate_agent import validate_claims


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

def _get_attr(obj, attr: str, default=None):
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _to_entry_metadata(metadata) -> EntryMetadata:
    """Convert a dict (from parse_entry_metadata) or pass-through an EntryMetadata."""
    if isinstance(metadata, EntryMetadata):
        return metadata
    return EntryMetadata(
        date=str(_get_attr(metadata, "date") or ""),
        start_location=str(_get_attr(metadata, "start_location") or ""),
        destination=str(_get_attr(metadata, "destination") or ""),
        miles_hiked=float(_get_attr(metadata, "miles_hiked") or 0.0),
        total_miles=float(_get_attr(metadata, "total_miles") or 0.0),
    )


def _entry_key(metadata) -> str:
    date = _get_attr(metadata, "date") or ""
    start = _get_attr(metadata, "start_location") or ""
    dest = _get_attr(metadata, "destination") or ""
    return f"{date}_{start}_{dest}"


# ---------------------------------------------------------------------------
# Deserialise cached JSON dicts back to dataclass objects
# ---------------------------------------------------------------------------

def _deserialise_claim(d: dict) -> Claim:
    return Claim(type=d.get("type", ""), text=d.get("text", ""))


def _deserialise_draft(d: dict) -> DraftFacts:
    return DraftFacts(
        trail_section_summary=d.get("trail_section_summary", ""),
        claims=[_deserialise_claim(c) for c in d.get("claims", [])],
        at_mile_start=d.get("at_mile_start"),
        at_mile_end=d.get("at_mile_end"),
        state=d.get("state"),
        nearest_town=d.get("nearest_town"),
    )


def _deserialise_validation(d: dict) -> ValidationResult:
    verified = [
        VerifiedClaim(
            claim=_deserialise_claim(vc["claim"]),
            source=vc.get("source", ""),
            confidence=float(vc.get("confidence", 0.0)),
        )
        for vc in d.get("verified", [])
    ]
    rejected = [_deserialise_claim(c) for c in d.get("rejected", [])]
    return ValidationResult(
        verified=verified,
        rejected=rejected,
        corrections=d.get("corrections", []),
    )


def _deserialise_weather(d: dict) -> Optional[WeatherFacts]:
    if not d:
        return None
    coords_raw = d.get("coords")
    coords = tuple(coords_raw) if coords_raw else None
    return WeatherFacts(
        high_f=d.get("high_f"),
        low_f=d.get("low_f"),
        precip_in=d.get("precip_in"),
        conditions=d.get("conditions"),
        source=d.get("source", ""),
        coords=coords,
        caveat=d.get("caveat"),
    )


def _deserialise_town_events(d: dict) -> TownEventsResult:
    return TownEventsResult(
        event=d.get("event"),
        source=d.get("source"),
        confidence=d.get("confidence"),
    )


# ---------------------------------------------------------------------------
# Weather fetch wrapper
# ---------------------------------------------------------------------------

def _fetch_weather_safe(metadata: EntryMetadata) -> Optional[WeatherFacts]:
    """Fetch weather if coordinates are resolvable; returns None on any failure."""
    try:
        from scripts.facts.location_resolver import resolve_coords
        from scripts.facts.weather_agent import fetch_weather

        coords = resolve_coords(metadata.start_location, metadata.destination)
        if coords is None:
            return None
        lat, lon = coords
        return fetch_weather(metadata.date, lat, lon)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Single-entry pipeline
# ---------------------------------------------------------------------------

def enrich_entry(
    metadata,
    entry_text: str,
    cache_dir,
    skip_firecrawl: bool = True,
) -> str:
    """Run the facts pipeline for one journal entry and return the enriched text.

    Each pipeline pass is cached so re-runs are cheap.
    If the entry already has frontmatter it is returned unchanged.
    """
    if has_frontmatter(entry_text):
        return entry_text

    em = _to_entry_metadata(metadata)
    cache = EntryCache(Path(cache_dir), _entry_key(em))

    # --- Pass 1: draft ---
    cached_draft = cache.load_pass("draft")
    if cached_draft:
        draft = _deserialise_draft(cached_draft)
    else:
        draft = draft_section_facts(em)
        cache.save_pass("draft", draft)

    # --- Pass 2: validation ---
    cached_val = cache.load_pass("validation")
    if cached_val:
        validation = _deserialise_validation(cached_val)
    else:
        validation = validate_claims(em, draft)
        cache.save_pass("validation", validation)

    # --- Pass 3: weather ---
    cached_weather = cache.load_pass("weather")
    if cached_weather:
        weather = _deserialise_weather(cached_weather)
    else:
        weather = _fetch_weather_safe(em)
        cache.save_pass("weather", dataclasses.asdict(weather) if weather else {})

    # --- Pass 4: town events ---
    cached_town = cache.load_pass("town_events")
    if cached_town:
        town_events = _deserialise_town_events(cached_town)
    else:
        town_events = fetch_town_events(em)
        cache.save_pass("town_events", town_events)

    # --- Pass 5: compile + frontmatter ---
    cached_fm = cache.load_pass("frontmatter")
    if cached_fm:
        frontmatter_str = cached_fm["frontmatter"]
    else:
        compiled = compile_facts(validation, weather, town_events, em, draft)
        frontmatter_str = build_frontmatter(em, compiled)
        cache.save_pass("frontmatter", frontmatter_str)

    return inject_frontmatter(entry_text, frontmatter_str)


# ---------------------------------------------------------------------------
# Journal-level pipeline
# ---------------------------------------------------------------------------

def enrich_journal(
    input_path,
    output_path,
    cache_dir,
    limit: Optional[int] = None,
    start: int = 1,
) -> None:
    """Enrich all entries in a journal file with YAML frontmatter.

    Args:
        input_path:  path to the source journal text file
        output_path: path for the enriched output file
        cache_dir:   directory for per-entry cache subdirectories
        limit:       maximum number of entries to process (None = all)
        start:       1-based entry index to start processing from
    """
    from scripts.enhance_entries import parse_entry_metadata

    input_path = Path(input_path)
    output_path = Path(output_path)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    content = input_path.read_text(encoding="utf-8")
    raw_entries = content.split("\n---\n")

    enriched: list = []
    processed = 0

    for idx, entry in enumerate(raw_entries, 1):
        entry_stripped = entry.strip()
        if not entry_stripped:
            enriched.append(entry)
            continue

        if idx < start:
            enriched.append(entry)
            continue

        if limit is not None and processed >= limit:
            enriched.append(entry)
            continue

        metadata = parse_entry_metadata(entry_stripped)
        if not metadata:
            enriched.append(entry)
            continue

        try:
            result = enrich_entry(metadata, entry_stripped, cache_dir)
            enriched.append(result)
        except Exception as exc:
            # Never drop an entry on error; preserve original text
            print(f"[WARNING] Entry {idx} enrichment failed: {exc}")
            enriched.append(entry)

        processed += 1

    output_path.write_text("\n---\n".join(enriched), encoding="utf-8")
    print(f"[INFO] Wrote {len(enriched)} entries to {output_path}")
