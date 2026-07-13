"""Tests for mile-range segment guide descriptions."""
from scripts.facts.segment_guide import (
    build_segment_description,
    guides_overlapping,
    resolve_mile_range,
)


def test_guides_overlapping_smokies_exit():
    guides = guides_overlapping(260, 275)
    names = [g["name"] for g in guides]
    assert any("Smokies" in n or "Cherokee" in n or "balds" in n.lower() for n in names)


def test_resolve_mile_range_from_trip_miles():
    start, end = resolve_mile_range("Unknown", "Roaring Fork Shelter", 11.5, 274.8)
    assert end == 274.8
    assert start is not None
    assert start < end


def test_build_segment_description_has_rich_text():
    summary, claims, meta = build_segment_description(
        "Groundhog Creek Shelter",
        "Roaring Fork Shelter",
        11.5,
        274.8,
    )
    assert summary
    assert "AT miles" in summary
    assert meta.get("segment_name")
    assert len(claims) >= 2


def test_build_segment_description_katahdin():
    summary, _, meta = build_segment_description(
        "The Birches Lean-tos",
        "Baxter Peak, Mount Katahdin",
        5.2,
        2179.5,
    )
    assert "Katahdin" in summary or "Baxter" in summary
    assert meta["at_mile_end"] >= 2150
