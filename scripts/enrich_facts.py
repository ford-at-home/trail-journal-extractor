"""CLI entry point for journal frontmatter enrichment.

Usage:
    python scripts/enrich_facts.py journal.txt \\
        --output out.txt \\
        --cache cache/facts \\
        --limit 10
"""
import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="enrich_facts",
        description="Enrich an AT journal with YAML frontmatter facts.",
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input journal text file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path for the enriched output file (default: <input>_facts.txt).",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("cache/facts"),
        help="Directory for per-entry cache (default: cache/facts).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of entries to process.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="1-based entry index to start from (default: 1).",
    )
    parser.add_argument(
        "--use-firecrawl",
        action="store_true",
        help="Enable firecrawl for town event searches on town days",
    )
    parser.add_argument(
        "--refresh-trail",
        action="store_true",
        help="Recompute trail section facts only (keep weather/town cache)",
    )
    parser.add_argument(
        "--skip-firecrawl",
        action="store_true",
        help="Deprecated: firecrawl is off by default; use --use-firecrawl to enable",
    )

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"ERROR: Input file not found: {args.input_file}", file=sys.stderr)
        return 1

    if args.output is None:
        args.output = args.input_file.parent / f"{args.input_file.stem}_facts.txt"

    from scripts.facts.orchestrator import enrich_journal

    print(f"[INFO] Input:  {args.input_file}")
    print(f"[INFO] Output: {args.output}")
    print(f"[INFO] Cache:  {args.cache}")
    if args.limit:
        print(f"[INFO] Limit:  {args.limit} entries")

    try:
        enrich_journal(
            input_path=args.input_file,
            output_path=args.output,
            cache_dir=args.cache,
            limit=args.limit,
            start=args.start,
            use_firecrawl=args.use_firecrawl,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
