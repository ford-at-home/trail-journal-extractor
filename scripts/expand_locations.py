#!/usr/bin/env python3
"""Add journal locations missing from at_locations.json using Nominatim geocoding."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from scripts.facts.location_resolver import lookup, normalize_name

JOURNAL = Path("examples/uncle-frank/journal.txt")
LOCATIONS = Path("data/at_locations.json")
USER_AGENT = "trail-journal-extractor/1.0 (example journal geocoder)"


def parse_locations(journal_text: str) -> set[str]:
    names: set[str] = set()
    for line in journal_text.splitlines():
        if line.startswith("**Start Location:**"):
            names.add(line.split(":", 1)[1].strip())
        elif line.startswith("# "):
            _, _, dest = line.partition(" — ")
            if dest:
                names.add(dest.strip())
    return {n for n in names if n and n not in {"Unknown", "Gear List"}}


def geocode(name: str) -> dict | None:
    # Prefer town in parentheses
    town_match = re.search(r"\(([^)]+)\)", name)
    query = town_match.group(1) if town_match else name
    query = f"{query}, Appalachian Trail"
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1}
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    if not data:
        return None
    hit = data[0]
    return {
        "name": name,
        "lat": float(hit["lat"]),
        "lon": float(hit["lon"]),
        "state": _guess_state(hit.get("display_name", "")),
        "at_mile": None,
        "is_town": bool(town_match) or any(k in name.lower() for k in ("motel", "hotel", "town")),
    }


def _guess_state(display_name: str) -> str:
    parts = [p.strip() for p in display_name.split(",")]
    for part in reversed(parts):
        if len(part) == 2 and part.isalpha():
            return part.upper()
    return "US"


def main() -> None:
    journal_text = JOURNAL.read_text(encoding="utf-8")
    existing = json.loads(LOCATIONS.read_text(encoding="utf-8"))
    existing_names = {normalize_name(loc["name"]) for loc in existing}

    missing = [n for n in sorted(parse_locations(journal_text)) if normalize_name(n) not in existing_names]
    print(f"Missing locations: {len(missing)}")

    added = 0
    for name in missing:
        try:
            loc = geocode(name)
            if loc:
                existing.append(loc)
                existing_names.add(normalize_name(name))
                added += 1
                print(f"  + {name} -> {loc['lat']:.4f}, {loc['lon']:.4f}")
        except Exception as exc:
            print(f"  ! {name}: {exc}")
        time.sleep(1.1)  # Nominatim rate limit

    LOCATIONS.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(f"Added {added} locations ({len(existing)} total)")


if __name__ == "__main__":
    main()
