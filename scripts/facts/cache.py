"""File-based per-entry cache for the facts pipeline.

Directory layout:
    <cache_dir>/<entry_key>/
        draft.json
        validation.json
        weather.json
        town_events.json
        frontmatter.yaml

Pass names: "draft", "validation", "weather", "town_events", "frontmatter"
"""
import dataclasses
import json
import re
from pathlib import Path
from typing import Optional


_PASS_FILES = {
    "draft": "draft.json",
    "validation": "validation.json",
    "weather": "weather.json",
    "town_events": "town_events.json",
    "frontmatter": "frontmatter.yaml",
}

_REQUIRED_PASSES = list(_PASS_FILES.keys())


def _safe_key(entry_key: str) -> str:
    """Sanitise an entry key for use as a directory name."""
    return re.sub(r"[^\w\-]", "_", entry_key)[:128]


def _serialise(data) -> str:
    """Convert a dataclass or dict to JSON string."""
    if dataclasses.is_dataclass(data) and not isinstance(data, type):
        return json.dumps(dataclasses.asdict(data), indent=2, ensure_ascii=False)
    if isinstance(data, dict):
        return json.dumps(data, indent=2, ensure_ascii=False)
    return str(data)


class EntryCache:
    """Cache for a single journal entry's pipeline passes."""

    def __init__(self, cache_dir: Path, entry_key: str):
        self.entry_dir = Path(cache_dir) / _safe_key(entry_key)
        self.entry_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, pass_name: str) -> Path:
        filename = _PASS_FILES.get(pass_name, f"{pass_name}.json")
        return self.entry_dir / filename

    def load_pass(self, pass_name: str) -> Optional[dict]:
        """Load a cached pass.  Returns a dict (or {"frontmatter": str}) or None."""
        path = self._path(pass_name)
        if not path.exists():
            return None
        try:
            text = path.read_text(encoding="utf-8")
            if pass_name == "frontmatter":
                return {"frontmatter": text}
            return json.loads(text)
        except (json.JSONDecodeError, OSError):
            return None

    def save_pass(self, pass_name: str, data) -> None:
        """Persist a pass result.

        Accepts dataclass instances, dicts, or plain strings (for frontmatter).
        """
        path = self._path(pass_name)
        if pass_name == "frontmatter":
            if isinstance(data, dict):
                text = data.get("frontmatter", "")
            else:
                text = str(data)
            path.write_text(text, encoding="utf-8")
        else:
            path.write_text(_serialise(data), encoding="utf-8")

    def is_complete(self) -> bool:
        """Return True when every required pass file exists on disk."""
        return all(self._path(p).exists() for p in _REQUIRED_PASSES)

    def completed_passes(self) -> list:
        """Return list of pass names that have been written."""
        return [p for p in _REQUIRED_PASSES if self._path(p).exists()]
