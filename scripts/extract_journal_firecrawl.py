#!/usr/bin/env python3
"""Extract a TrailJournals.com journal using the Firecrawl CLI (Cloudflare-safe)."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ENTRY_URL_RE = re.compile(
    r"https://www\.trailjournals\.com/journal/entry/(\d+)"
)
FIELD_PATTERNS = {
    "date": re.compile(
        r"^(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday), "
        r"(January|February|March|April|May|June|July|August|September|October|November|December) "
        r"\d{1,2}, \d{4}$",
        re.MULTILINE,
    ),
    "destination": re.compile(r"^Destination:[ \t]*([^\n]*)", re.MULTILINE),
    "start": re.compile(r"^Start Location:[ \t]*([^\n]*)", re.MULTILINE),
    "miles_today": re.compile(r"^Today'?s Miles:\s*([\d.]+)", re.MULTILINE),
    "trip_miles": re.compile(r"^Trip Miles:\s*([\d.]+)", re.MULTILINE),
}


def _firecrawl_scrape(url: str, output: Path) -> bool:
    result = subprocess.run(
        ["firecrawl", "scrape", url, "-o", str(output)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and output.exists()


def _first_match(pattern: re.Pattern[str], text: str, group: int = 0) -> str | None:
    match = pattern.search(text)
    return match.group(group).strip() if match else None


def _parse_date(text: str) -> str | None:
    full = _first_match(FIELD_PATTERNS["date"], text, group=0)
    if full:
        return full
    # Breadcrumb fallback: "7. February 07, 2010"
    crumb = re.search(
        r"\d+\.\s+((?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},\s+\d{4})",
        text,
    )
    if crumb:
        return crumb.group(1).strip()
    return None


def _extract_body(text: str, trip_miles_line: str | None) -> str:
    """Pull journal prose from scraped markdown."""
    if not trip_miles_line:
        return text.strip()

    idx = text.find(trip_miles_line)
    if idx == -1:
        return text.strip()

    after = text[idx + len(trip_miles_line) :]
    # Drop duplicate metadata block that TrailJournals repeats
    lines = after.splitlines()
    body_lines: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if not started:
            if stripped.startswith("Destination:") or stripped.startswith("Start Location:"):
                continue
            if stripped.startswith("Today's Miles:") or stripped.startswith("Trip Miles:"):
                continue
            if not stripped:
                continue
            if stripped.startswith("[First]") or stripped.startswith("### Hiker Entries"):
                break
            started = True
        if stripped.startswith("[First]") or stripped.startswith("### Hiker Entries"):
            break
        body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return body or text.strip()


def parse_entry_markdown(text: str) -> dict:
    date = _parse_date(text)
    destination = _first_match(FIELD_PATTERNS["destination"], text, group=1) or ""
    if not destination or destination.lower() in {"view entry", "n/a"}:
        # Title line fallback: "# Uncle Frank's 2010 Appalachian Trail Journal" skipped;
        # use table link text or generic planning label for zero-mile pre-hike posts
        if _first_match(FIELD_PATTERNS["miles_today"], text, group=1) == "0" and not destination:
            destination = "Pre-Hike Planning"
        else:
            destination = destination or "Trail Journal Entry"
    start = _first_match(FIELD_PATTERNS["start"], text, group=1) or "Unknown"
    miles_today = _first_match(FIELD_PATTERNS["miles_today"], text, group=1) or "0"
    trip_miles = _first_match(FIELD_PATTERNS["trip_miles"], text, group=1) or "0"

    trip_line = None
    for line in text.splitlines():
        if line.strip().startswith("Trip Miles:"):
            trip_line = line.strip()
            break

    body = _extract_body(text, trip_line)
    return {
        "date": date or "Unknown Date",
        "destination": destination,
        "start_location": start,
        "miles_today": miles_today,
        "trip_miles": trip_miles,
        "body": body,
    }


def format_entry(entry: dict) -> str:
    return (
        f"# {entry['date']} — {entry['destination']}\n"
        f"**Start Location:** {entry['start_location']}\n"
        f"**Miles Today:** {entry['miles_today']}\n"
        f"**Trip Miles:** {entry['trip_miles']}\n\n"
        f"{entry['body']}\n"
    )


TABLE_ENTRY_RE = re.compile(
    r"\| \[[^\]]*\]\(https://www\.trailjournals\.com/journal/entry/(\d+)\) \| "
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
)


def fetch_entry_urls(journal_id: str, scratch: Path) -> list[str]:
    index_url = f"https://www.trailjournals.com/journal/entries/{journal_id}"
    index_file = scratch / "entries_index.md"
    if not _firecrawl_scrape(index_url, index_file):
        raise RuntimeError(f"Failed to scrape journal index: {index_url}")

    text = index_file.read_text(encoding="utf-8")
    ids = list(dict.fromkeys(TABLE_ENTRY_RE.findall(text)))
    if not ids:
        # Fallback: any entry links on the page
        ids = list(dict.fromkeys(ENTRY_URL_RE.findall(text)))
    return [f"https://www.trailjournals.com/journal/entry/{eid}" for eid in ids]


def scrape_entry(url: str, scratch: Path) -> tuple[str, dict | None]:
    entry_id = url.rstrip("/").split("/")[-1]
    out = scratch / f"entry_{entry_id}.md"
    if not _firecrawl_scrape(url, out):
        return url, None
    try:
        parsed = parse_entry_markdown(out.read_text(encoding="utf-8"))
        return url, parsed
    except Exception:
        return url, None


def build_journal(
    journal_id: str,
    output_file: Path,
    workers: int = 8,
    limit: int | None = None,
) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tj_extract_") as tmp:
        scratch = Path(tmp)
        urls = fetch_entry_urls(journal_id, scratch)
        if limit:
            urls = urls[:limit]

        print(f"Found {len(urls)} entries. Scraping with {workers} workers...")
        results: list[tuple[str, dict | None]] = []

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(scrape_entry, url, scratch): url for url in urls}
            for i, future in enumerate(as_completed(futures), 1):
                url, entry = future.result()
                status = "ok" if entry else "FAIL"
                print(f"[{i}/{len(urls)}] {status} {url}")
                results.append((url, entry))

        # Preserve index page order
        url_order = {url: idx for idx, url in enumerate(urls)}
        results.sort(key=lambda pair: url_order[pair[0]])

        entries: list[str] = []
        for url, entry in results:
            if entry:
                entries.append(format_entry(entry))
            else:
                print(f"WARNING: skipped {url}", file=sys.stderr)

        output_file.write_text("\n---\n\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")
        print(f"Wrote {len(entries)} entries to {output_file}")
        return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract TrailJournals journal via Firecrawl")
    parser.add_argument("journal_id", help="TrailJournals journal ID (e.g. 10467)")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output journal text file")
    parser.add_argument("--workers", type=int, default=8, help="Parallel scrape workers")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of entries")
    args = parser.parse_args()

    try:
        count = build_journal(args.journal_id, args.output, workers=args.workers, limit=args.limit)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0 if count else 1


if __name__ == "__main__":
    sys.exit(main())
