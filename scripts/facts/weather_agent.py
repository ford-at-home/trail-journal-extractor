import requests
from scripts.facts.models import WeatherFacts

_OPEN_METEO_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
    "?latitude={lat}&longitude={lon}"
    "&start_date={date}&end_date={date}"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
    "&temperature_unit=fahrenheit&precipitation_unit=inch"
)

# WMO Weather interpretation codes → human-readable strings
_WMO_CONDITIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with light hail",
    99: "Thunderstorm with heavy hail",
}


def _wmo_to_conditions(code: int) -> str:
    return _WMO_CONDITIONS.get(code, f"Unknown (WMO {code})")


def fetch_weather(date: str, lat: float, lon: float) -> WeatherFacts:
    """
    Fetch historical weather for a given date and coordinates from Open-Meteo archive.

    Args:
        date: ISO date string, e.g. "2010-03-15"
        lat: latitude (float)
        lon: longitude (float)

    Returns:
        WeatherFacts populated from the API response, with caveat set on any error.
    """
    url = _OPEN_METEO_URL.format(lat=lat, lon=lon, date=date)
    coords = (lat, lon)
    source = "Open-Meteo archive"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return WeatherFacts(
            high_f=None,
            low_f=None,
            precip_in=None,
            conditions=None,
            source=source,
            coords=coords,
            caveat="Request timed out fetching weather data.",
        )
    except requests.exceptions.RequestException as exc:
        return WeatherFacts(
            high_f=None,
            low_f=None,
            precip_in=None,
            conditions=None,
            source=source,
            coords=coords,
            caveat=f"HTTP error fetching weather data: {exc}",
        )
    except ValueError:
        return WeatherFacts(
            high_f=None,
            low_f=None,
            precip_in=None,
            conditions=None,
            source=source,
            coords=coords,
            caveat="Invalid JSON in weather response.",
        )

    try:
        daily = data["daily"]
        high_f = daily["temperature_2m_max"][0]
        low_f = daily["temperature_2m_min"][0]
        precip_in = daily["precipitation_sum"][0]
        wmo_code = daily["weathercode"][0]
        conditions = _wmo_to_conditions(int(wmo_code))
    except (KeyError, IndexError, TypeError) as exc:
        return WeatherFacts(
            high_f=None,
            low_f=None,
            precip_in=None,
            conditions=None,
            source=source,
            coords=coords,
            caveat=f"Unexpected response structure: {exc}",
        )

    return WeatherFacts(
        high_f=high_f,
        low_f=low_f,
        precip_in=precip_in,
        conditions=conditions,
        source=source,
        coords=coords,
        caveat=None,
    )
