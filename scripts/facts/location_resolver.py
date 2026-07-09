import json
import re
from pathlib import Path
from typing import Optional

_LOCATIONS_PATH = Path(__file__).parent.parent.parent / "data" / "at_locations.json"

_locations: Optional[list] = None


def _load_locations() -> list:
    global _locations
    if _locations is None:
        with open(_LOCATIONS_PATH, "r") as f:
            _locations = json.load(f)
    return _locations


def normalize_name(name: str) -> str:
    """Lowercase, strip parentheticals, and collapse whitespace."""
    # Remove parenthetical suffixes like "(Helen, GA)"
    name = re.sub(r"\s*\(.*?\)", "", name)
    return name.lower().strip()


def lookup(name: str) -> Optional[dict]:
    """Look up a location by name. Returns dict with lat, lon, state, at_mile, is_town."""
    normalized = normalize_name(name)
    for loc in _load_locations():
        if normalize_name(loc["name"]) == normalized:
            return loc
    return None


def extract_town_from_location(location: str) -> Optional[str]:
    """Extract town name from a parenthetical, e.g. 'EconoLodge Motel (Helen, GA)' -> 'Helen, GA'."""
    match = re.search(r"\(([^)]+)\)", location)
    if match:
        return match.group(1).strip()
    return None


_TRAIL_LODGES = frozenset(
    [
        "hike inn",
        "neel gap hostel",
        "blueberry patch hostel",
        "standing bear farm hostel",
        "mountain harbour hostel",
        "the place",
        "woods hole hostel",
        "bear's den hostel",
        "harper's ferry hostel",
        "hikers welcome hostel",
        "shaw's boarding house",
    ]
)

_TOWN_LODGING_KEYWORDS = frozenset(["motel", "hotel", "econolodge", "travelodge", "holiday inn"])


def _metadata_field(metadata, field: str) -> str:
    if isinstance(metadata, dict):
        return str(metadata.get(field) or "")
    return str(getattr(metadata, field, "") or "")


def is_town_day(metadata) -> bool:
    """
    Heuristic: return True when the entry is a town stop worth researching.

    Trail shelters and backcountry inns are excluded. Town days are entries with
    an explicit town in parentheses, a known town location, or commercial lodging.
    """
    fields = [
        _metadata_field(metadata, "destination"),
        _metadata_field(metadata, "start_location"),
    ]

    for field_val in fields:
        if extract_town_from_location(field_val):
            return True

        normalized = normalize_name(field_val)
        if normalized in _TRAIL_LODGES:
            continue

        loc = lookup(field_val)
        if loc and loc.get("is_town"):
            return True

        lowered = field_val.lower()
        if any(kw in lowered for kw in _TOWN_LODGING_KEYWORDS):
            return True

    return False


def resolve_coords(start: str, destination: str) -> Optional[tuple]:
    """
    Return midpoint (lat, lon) between start and destination lookups.
    Falls back to whichever single point is found, or None if neither found.
    """
    start_loc = lookup(start)
    dest_loc = lookup(destination)

    if start_loc and dest_loc:
        lat = (start_loc["lat"] + dest_loc["lat"]) / 2
        lon = (start_loc["lon"] + dest_loc["lon"]) / 2
        return (lat, lon)

    for loc in (start_loc, dest_loc):
        if loc:
            return (loc["lat"], loc["lon"])

    return None
