"""Town events agent for AT journal entries.

For the pilot:
  - Returns TownEventsResult(event=None) for non-town days.
  - Attempts a firecrawl search on town days only if firecrawl is available.
"""
import json
import shutil
import subprocess

from scripts.facts.models import TownEventsResult


def _get_attr(obj, attr: str, default=""):
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _firecrawl_search_event(town: str, date: str) -> TownEventsResult:
    """Query firecrawl for events in a town on a given date. Never invents sources."""
    query = f"Appalachian Trail town events {town} {date}"
    try:
        result = subprocess.run(
            ["firecrawl", "search", "--json", query[:200]],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return TownEventsResult(event=None)
        data = json.loads(result.stdout)
        items = data.get("data") or data.get("results") or []
        if items:
            first = items[0]
            title = first.get("title") or first.get("snippet") or ""
            url = first.get("url") or ""
            if title:
                source = url if url else "firecrawl web search"
                return TownEventsResult(
                    event=title[:300],
                    source=source,
                    confidence=0.5,
                )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return TownEventsResult(event=None)


def fetch_town_events(metadata) -> TownEventsResult:
    """Return town event information for an entry.

    Returns TownEventsResult(event=None) when:
      - The entry is not a town day, or
      - firecrawl is unavailable and no local data applies.
    """
    from scripts.facts.location_resolver import extract_town_from_location, is_town_day

    if not is_town_day(metadata):
        return TownEventsResult(event=None)

    # Resolve the nearest town name for search
    dest = _get_attr(metadata, "destination", "")
    start = _get_attr(metadata, "start_location", "")
    date = _get_attr(metadata, "date", "")

    town = (
        extract_town_from_location(dest)
        or extract_town_from_location(start)
        or dest
        or start
    )

    if shutil.which("firecrawl") and town and date:
        return _firecrawl_search_event(town, date)

    return TownEventsResult(event=None)
