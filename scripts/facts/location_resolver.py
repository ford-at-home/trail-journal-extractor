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


_TOWN_KEYWORDS = frozenset(
    ["motel", "hostel", "inn", "lodge", "hotel", "b&b", "bed and breakfast"]
)


def is_town_day(metadata) -> bool:
    """
    Heuristic: return True if the entry likely represents a town stay rather
    than a trail camp. Checks:
      - destination or start_location contains a lodging keyword
      - destination or start_location has a parenthetical town suffix
      - miles_hiked == 0 (zero-mile rest/zero day)
    """
    fields = [
        getattr(metadata, "destination", "") or "",
        getattr(metadata, "start_location", "") or "",
    ]
    for field_val in fields:
        lowered = field_val.lower()
        if any(kw in lowered for kw in _TOWN_KEYWORDS):
            return True
        if re.search(r"\([^)]+,\s*[A-Z]{2}\)", field_val):
            return True

    miles = getattr(metadata, "miles_hiked", None)
    if miles is not None and miles == 0:
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
