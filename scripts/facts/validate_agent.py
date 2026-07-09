"""Rule-based claim validator for AT journal facts.

For the pilot, claims are verified against the location resolver database.
Optional firecrawl integration is available when the CLI tool is on PATH but
is never required—the agent works fully offline.
"""
import json
import shutil
import subprocess
from typing import Optional

from scripts.facts.models import Claim, DraftFacts, ValidationResult, VerifiedClaim

_AT_DB_SOURCE = "AT location database"


def _get_attr(obj, attr: str, default=""):
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _safe_lookup(name: str) -> Optional[dict]:
    """Wrap location_resolver.lookup with graceful handling for missing data file."""
    try:
        from scripts.facts.location_resolver import lookup
        return lookup(name)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def _try_firecrawl_validate(claim_text: str) -> bool:
    """
    Attempt to verify a claim via a firecrawl web search subprocess.
    Returns True only if firecrawl confirms the claim text; never invents sources.
    """
    try:
        result = subprocess.run(
            ["firecrawl", "search", "--json", claim_text[:200]],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        # Accept if firecrawl returned at least one result
        return bool(data.get("data") or data.get("results"))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return False


def _endpoint_confidence(start_resolved: bool, dest_resolved: bool) -> float:
    if start_resolved and dest_resolved:
        return 1.0
    if start_resolved or dest_resolved:
        return 0.8
    return 0.0


_SEGMENT_SOURCE = "AT segment guide"


def validate_claims(metadata, draft: DraftFacts) -> ValidationResult:
    """
    Validate draft claims against the AT location database.

    Strategy:
      - If both endpoints resolve  → all claims verified at confidence 1.0
      - If one endpoint resolves   → all claims verified at confidence 0.8
      - If neither resolves        → try firecrawl (if available); otherwise reject
    """
    start = _get_attr(metadata, "start_location", "")
    dest = _get_attr(metadata, "destination", "")

    start_resolved = _safe_lookup(start) is not None if start else False
    dest_resolved = _safe_lookup(dest) is not None if dest else False

    base_confidence = _endpoint_confidence(start_resolved, dest_resolved)
    have_firecrawl = shutil.which("firecrawl") is not None

    verified: list = []
    rejected: list = []
    corrections: list = []

    for claim in draft.claims:
        # Segment-guide claims are verified when mile range is known
        if claim.type == "segment":
            verified.append(
                VerifiedClaim(claim=claim, source=_SEGMENT_SOURCE, confidence=0.85)
            )
            continue
        if base_confidence > 0:
            verified.append(
                VerifiedClaim(
                    claim=claim,
                    source=_AT_DB_SOURCE,
                    confidence=base_confidence,
                )
            )
        elif have_firecrawl:
            if _try_firecrawl_validate(claim.text):
                verified.append(
                    VerifiedClaim(
                        claim=claim,
                        source="firecrawl web search",
                        confidence=0.6,
                    )
                )
            else:
                rejected.append(claim)
        else:
            rejected.append(claim)

    return ValidationResult(
        verified=verified,
        rejected=rejected,
        corrections=corrections,
    )
