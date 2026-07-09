import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.facts.weather_agent import fetch_weather, _wmo_to_conditions
from scripts.facts.models import WeatherFacts

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_weather_response.json"


@pytest.fixture
def sample_response_data():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def _make_mock_response(data: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


class TestWmoToConditions:
    def test_clear_sky(self):
        assert _wmo_to_conditions(0) == "Clear sky"

    def test_slight_rain(self):
        assert _wmo_to_conditions(61) == "Slight rain"

    def test_thunderstorm(self):
        assert _wmo_to_conditions(95) == "Thunderstorm"

    def test_heavy_snow(self):
        assert _wmo_to_conditions(75) == "Heavy snow"

    def test_unknown_code(self):
        result = _wmo_to_conditions(999)
        assert "999" in result


class TestFetchWeather:
    def test_returns_weather_facts_type(self, sample_response_data):
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.return_value = _make_mock_response(sample_response_data)
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert isinstance(result, WeatherFacts)

    def test_parses_temperature_high(self, sample_response_data):
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.return_value = _make_mock_response(sample_response_data)
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.high_f == pytest.approx(52.3)

    def test_parses_temperature_low(self, sample_response_data):
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.return_value = _make_mock_response(sample_response_data)
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.low_f == pytest.approx(38.1)

    def test_parses_precipitation(self, sample_response_data):
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.return_value = _make_mock_response(sample_response_data)
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.precip_in == pytest.approx(0.12)

    def test_parses_conditions_from_wmo_code(self, sample_response_data):
        # Fixture has weathercode 61 → "Slight rain"
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.return_value = _make_mock_response(sample_response_data)
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.conditions == "Slight rain"

    def test_source_is_open_meteo(self, sample_response_data):
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.return_value = _make_mock_response(sample_response_data)
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert "Open-Meteo" in result.source

    def test_coords_match_input(self, sample_response_data):
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.return_value = _make_mock_response(sample_response_data)
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.coords == (34.69, -84.154)

    def test_no_caveat_on_success(self, sample_response_data):
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.return_value = _make_mock_response(sample_response_data)
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.caveat is None

    def test_request_exception_returns_caveat(self):
        import requests as req_lib
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.side_effect = req_lib.exceptions.ConnectionError("Network error")
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.caveat is not None
        assert result.high_f is None
        assert result.low_f is None

    def test_timeout_returns_caveat(self):
        import requests as req_lib
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.side_effect = req_lib.exceptions.Timeout()
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.caveat is not None
        assert "timed out" in result.caveat.lower()

    def test_http_error_returns_caveat(self):
        import requests as req_lib
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = req_lib.exceptions.HTTPError(
                "500 Server Error"
            )
            mock_get.return_value = mock_resp
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.caveat is not None

    def test_malformed_json_returns_caveat(self):
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.side_effect = ValueError("No JSON")
            mock_get.return_value = mock_resp
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.caveat is not None

    def test_missing_daily_key_returns_caveat(self):
        with patch("scripts.facts.weather_agent.requests.get") as mock_get:
            mock_get.return_value = _make_mock_response({"latitude": 34.69})
            result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert result.caveat is not None
        assert result.high_f is None

    @pytest.mark.integration
    def test_live_api_call(self):
        """Calls the real Open-Meteo API. Excluded from normal test runs."""
        result = fetch_weather("2010-03-15", 34.69, -84.154)
        assert isinstance(result, WeatherFacts)
        assert result.high_f is not None or result.caveat is not None
