import pytest
from scripts.facts.models import EntryMetadata
from scripts.facts.location_resolver import (
    lookup,
    normalize_name,
    extract_town_from_location,
    is_town_day,
    resolve_coords,
)


class TestNormalizeName:
    def test_lowercase(self):
        assert normalize_name("Hawk Mountain Shelter") == "hawk mountain shelter"

    def test_strips_parenthetical(self):
        assert normalize_name("EconoLodge (Helen, GA)") == "econolodge"

    def test_strips_whitespace(self):
        assert normalize_name("  Low Gap Shelter  ") == "low gap shelter"

    def test_parenthetical_with_inner_spaces(self):
        assert normalize_name("Best Western (Hiawassee, GA)") == "best western"


class TestLookup:
    def test_hawk_mountain_shelter(self):
        result = lookup("Hawk Mountain Shelter")
        assert result is not None
        assert abs(result["lat"] - 34.6899) < 0.01
        assert abs(result["lon"] - -84.154) < 0.01
        assert result["state"] == "GA"
        assert result["at_mile"] == pytest.approx(8.1)
        assert result["is_town"] is False

    def test_gooch_mountain_shelter(self):
        result = lookup("Gooch Mountain Shelter")
        assert result is not None
        assert result["state"] == "GA"
        assert result["at_mile"] == pytest.approx(15.8)

    def test_neel_gap_hostel(self):
        result = lookup("Neel Gap Hostel")
        assert result is not None
        assert result["state"] == "GA"

    def test_low_gap_shelter(self):
        result = lookup("Low Gap Shelter")
        assert result is not None
        assert result["at_mile"] == pytest.approx(38.5)

    def test_hiawassee_is_town(self):
        result = lookup("Hiawassee GA")
        assert result is not None
        assert result["is_town"] is True

    def test_helen_is_town(self):
        result = lookup("Helen GA")
        assert result is not None
        assert result["is_town"] is True

    def test_unknown_location_returns_none(self):
        assert lookup("Nowhere Special Shelter") is None

    def test_case_insensitive(self):
        result = lookup("hawk mountain shelter")
        assert result is not None

    def test_parenthetical_stripped_before_lookup(self):
        # "Neel Gap Hostel" should match with or without extra parens
        result = lookup("Hawk Mountain Shelter (GA)")
        assert result is not None


class TestExtractTownFromLocation:
    def test_extracts_town(self):
        assert extract_town_from_location("EconoLodge Motel (Helen, GA)") == "Helen, GA"

    def test_extracts_hiawassee(self):
        assert extract_town_from_location("Budget Inn (Hiawassee, GA)") == "Hiawassee, GA"

    def test_no_parenthetical_returns_none(self):
        assert extract_town_from_location("Hawk Mountain Shelter") is None

    def test_empty_string_returns_none(self):
        assert extract_town_from_location("") is None


class TestIsTownDay:
    def _make_metadata(self, destination="", start_location="", miles_hiked=10.0):
        return EntryMetadata(
            date="2010-03-15",
            start_location=start_location,
            destination=destination,
            miles_hiked=miles_hiked,
            total_miles=50.0,
        )

    def test_motel_in_destination(self):
        meta = self._make_metadata(destination="EconoLodge Motel (Helen, GA)")
        assert is_town_day(meta) is True

    def test_hostel_in_destination(self):
        meta = self._make_metadata(destination="Neel Gap Hostel")
        assert is_town_day(meta) is True

    def test_inn_in_destination(self):
        meta = self._make_metadata(destination="Hike Inn")
        assert is_town_day(meta) is True

    def test_hotel_in_destination(self):
        meta = self._make_metadata(destination="Holiday Hotel (Franklin, NC)")
        assert is_town_day(meta) is True

    def test_lodge_in_start(self):
        meta = self._make_metadata(start_location="Mountain Lodge (Hiawassee, GA)")
        assert is_town_day(meta) is True

    def test_parenthetical_state_in_destination(self):
        meta = self._make_metadata(destination="Some Place (Franklin, NC)")
        assert is_town_day(meta) is True

    def test_zero_miles(self):
        meta = self._make_metadata(destination="Hawk Mountain Shelter", miles_hiked=0)
        assert is_town_day(meta) is True

    def test_trail_shelter_not_town(self):
        meta = self._make_metadata(
            destination="Hawk Mountain Shelter",
            start_location="Springer Mountain",
            miles_hiked=8.1,
        )
        assert is_town_day(meta) is False

    def test_normal_hiking_day(self):
        meta = self._make_metadata(
            destination="Gooch Mountain Shelter",
            start_location="Hawk Mountain Shelter",
            miles_hiked=7.7,
        )
        assert is_town_day(meta) is False


class TestResolveCoords:
    def test_both_known(self):
        coords = resolve_coords("Hawk Mountain Shelter", "Gooch Mountain Shelter")
        assert coords is not None
        lat, lon = coords
        assert 34.0 < lat < 35.5
        assert -85.0 < lon < -83.0

    def test_one_unknown_falls_back_to_known(self):
        coords = resolve_coords("Hawk Mountain Shelter", "Nowhere Special")
        assert coords is not None
        lat, lon = coords
        assert abs(lat - 34.6899) < 0.01

    def test_both_unknown_returns_none(self):
        assert resolve_coords("Nowhere A", "Nowhere B") is None
