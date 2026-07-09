from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class EntryMetadata:
    date: str
    start_location: str
    destination: str
    miles_hiked: float
    total_miles: float


@dataclass
class Claim:
    type: str
    text: str


@dataclass
class DraftFacts:
    trail_section_summary: str
    claims: List[Claim]
    at_mile_start: Optional[float]
    at_mile_end: Optional[float]
    state: Optional[str]
    nearest_town: Optional[str]
    segment_name: Optional[str] = None
    region: Optional[str] = None


@dataclass
class VerifiedClaim:
    claim: Claim
    source: str
    confidence: float


@dataclass
class ValidationResult:
    verified: List[VerifiedClaim]
    rejected: List[Claim]
    corrections: List[str]


@dataclass
class WeatherFacts:
    high_f: Optional[float]
    low_f: Optional[float]
    precip_in: Optional[float]
    conditions: Optional[str]
    source: str
    coords: Optional[tuple]
    caveat: Optional[str] = None


@dataclass
class TownEventsResult:
    event: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class CompiledFacts:
    weather: Optional[WeatherFacts]
    trail_section: Optional[DraftFacts]
    town_events: Optional[TownEventsResult]
    confidence: float
    sources: List[str] = field(default_factory=list)


@dataclass
class FrontmatterData:
    date: str
    title: str
    start_location: str
    destination: str
    miles_hiked: float
    total_miles: float
    state: Optional[str] = None
    nearest_town: Optional[str] = None
    at_mile_start: Optional[float] = None
    at_mile_end: Optional[float] = None
    weather_high_f: Optional[float] = None
    weather_low_f: Optional[float] = None
    weather_precip_in: Optional[float] = None
    weather_conditions: Optional[str] = None
    weather_source: Optional[str] = None
    weather_caveat: Optional[str] = None
    trail_section_summary: Optional[str] = None
    town_event: Optional[str] = None
