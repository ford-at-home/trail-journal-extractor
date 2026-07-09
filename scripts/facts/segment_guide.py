"""Mile-range segment guides for rich per-hike trail section descriptions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from scripts.facts.models import Claim

_GUIDES_PATH = Path(__file__).parent.parent.parent / "data" / "at_segment_guides.json"
_LOCATIONS_PATH = Path(__file__).parent.parent.parent / "data" / "at_locations.json"

_guides: Optional[list] = None
_locations: Optional[list] = None


def _load_guides() -> list:
    global _guides
    if _guides is None:
        with open(_GUIDES_PATH, encoding="utf-8") as f:
            _guides = json.load(f)
    return _guides


def _load_locations() -> list:
    global _locations
    if _locations is None:
        with open(_LOCATIONS_PATH, encoding="utf-8") as f:
            _locations = json.load(f)
    return _locations


def guides_overlapping(mile_start: float, mile_end: float) -> list[dict]:
    """Return segment guides that overlap the hiked mile range."""
    lo, hi = (mile_start, mile_end) if mile_start <= mile_end else (mile_end, mile_start)
    return [
        g
        for g in _load_guides()
        if g["mile_end"] >= lo and g["mile_start"] <= hi
    ]


def landmarks_between(mile_start: float, mile_end: float, limit: int = 4) -> list[str]:
    """Notable named places with AT miles falling inside the hiked range."""
    lo, hi = (mile_start, mile_end) if mile_start <= mile_end else (mile_end, mile_start)
    hits = []
    for loc in _load_locations():
        mile = loc.get("at_mile")
        if mile is None or not (lo <= mile <= hi):
            continue
        hits.append((mile, loc["name"]))
    hits.sort(key=lambda x: x[0])
    return [name for _, name in hits[:limit]]


def resolve_mile_range(
    start_location: str,
    destination: str,
    miles_hiked: float,
    trip_miles: float,
) -> tuple[Optional[float], Optional[float]]:
    """Best-effort AT mile range for a day's hike."""
    from scripts.facts.location_resolver import lookup

    start_loc = lookup(start_location) if start_location else None
    dest_loc = lookup(destination) if destination else None

    mile_start = start_loc.get("at_mile") if start_loc else None
    mile_end = dest_loc.get("at_mile") if dest_loc else None

    if mile_end is None and trip_miles:
        mile_end = float(trip_miles)
    if mile_start is None and mile_end is not None and miles_hiked:
        mile_start = max(0.0, mile_end - float(miles_hiked))

    return mile_start, mile_end


def build_segment_description(
    start_location: str,
    destination: str,
    miles_hiked: float,
    trip_miles: float,
) -> tuple[str, list[Claim], dict]:
    """
    Return (summary_text, claims, meta) for the hiked segment.

    meta keys: segment_name, region, at_mile_start, at_mile_end
    """
    mile_start, mile_end = resolve_mile_range(
        start_location, destination, miles_hiked, trip_miles
    )

    if mile_start is None and mile_end is None:
        return "", [], {}

    if mile_start is None:
        mile_start = max(0.0, (mile_end or 0) - max(miles_hiked, 1))
    if mile_end is None:
        mile_end = mile_start + max(miles_hiked, 0)

    guides = guides_overlapping(mile_start, mile_end)
    if not guides:
        return "", [], {
            "segment_name": None,
            "region": None,
            "at_mile_start": mile_start,
            "at_mile_end": mile_end,
        }

    # Primary guide = the one containing the midpoint of the day's hike
    midpoint = (mile_start + mile_end) / 2
    primary = min(guides, key=lambda g: abs((g["mile_start"] + g["mile_end"]) / 2 - midpoint))

    between = landmarks_between(mile_start, mile_end)
    mile_label = f"AT miles {mile_start:.0f}–{mile_end:.0f}"

    parts = [
        f"{primary['name']} ({mile_label}): {primary['summary']}",
        primary["terrain"],
    ]
    if between:
        parts.append(f"Notable points along this leg include {', '.join(between)}.")
    elif primary.get("notable"):
        parts.append(
            "Landmarks in this corridor include "
            + ", ".join(primary["notable"][:4])
            + "."
        )

    summary = " ".join(parts)

    claims = [
        Claim("segment", primary["summary"]),
        Claim("terrain", primary["terrain"]),
        Claim("segment", f"Section: {primary['name']} ({primary['region']})."),
    ]
    if between:
        claims.append(
            Claim("landmark", f"Today's hike passes near: {', '.join(between)}.")
        )

    meta = {
        "segment_name": primary["name"],
        "region": primary["region"],
        "at_mile_start": round(mile_start, 1),
        "at_mile_end": round(mile_end, 1),
    }
    return summary, claims, meta
