# Uncle Frank — 2010 Appalachian Trail Journal

Example output from the trail journal facts enrichment pipeline.

| File | Description |
|------|-------------|
| `metadata.json` | Journal metadata (author, trail, dates, source URL) |
| `journal.txt` | Raw extracted entries from [TrailJournals.com](https://www.trailjournals.com/journal/10467) |
| `journal_facts.txt` | Enriched entries with YAML `facts` frontmatter on each post |

## Frontmatter format

Each entry is prefixed with structured facts:

```yaml
---
date: '2010-02-07'
start: Hike Inn
destination: Hawk Mountain Shelter
miles_today: 9.0
trip_miles: 9.0
facts:
  weather: High 40°F, low 23°F. Slight snow.
  trail_section: Northern Georgia approach to Springer...
  town_events: null
  confidence: high
  sources:
    - AT location database
    - Open-Meteo archive
---
```

## Regenerate

```bash
make uncle-frank          # Extract all ~133 entries via Firecrawl
make uncle-frank-facts    # Enrich with weather + trail facts (+ town events)
```

## About

- **Trail name:** Uncle Frank
- **Author:** Ford Prior
- **Hike:** Northbound AT thru-hike, January–June 2010
- **Finish:** Baxter Peak, Mount Katahdin (2,179.5 miles)
