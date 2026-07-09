"""Rule-based draft facts generator for AT journal entries.

Produces DraftFacts from entry metadata using a static AT location knowledge base.
No external services or AWS required—safe to run in pilot mode.
"""
from typing import Optional

from scripts.facts.models import Claim, DraftFacts


def _get_attr(obj, attr: str, default=""):
    """Retrieve a field from either a dataclass/object or a plain dict."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


# ---------------------------------------------------------------------------
# Static knowledge base
# ---------------------------------------------------------------------------

# Each entry: normalized substring to match → dict with:
#   state, at_mile, nearest_town (optional), claims, summary
_LOCATION_KNOWLEDGE = [
    {
        "keys": ["springer mountain"],
        "state": "Georgia",
        "at_mile": 0.0,
        "summary": "Springer Mountain (3,782 ft) is the southern terminus of the 2,190-mile Appalachian Trail.",
        "claims": [
            Claim("landmark", "Springer Mountain is the official southern terminus of the Appalachian Trail at 3,782 feet."),
            Claim("landmark", "A bronze plaque and a register box mark the AT's starting point at Springer Mountain's summit."),
            Claim("terrain", "Most northbound thru-hikers begin their journey at Springer Mountain in late winter or early spring."),
        ],
    },
    {
        "keys": ["amicalola falls"],
        "state": "Georgia",
        "at_mile": None,
        "summary": "Amicalola Falls State Park is the traditional gateway to Springer Mountain for northbound thru-hikers.",
        "claims": [
            Claim("landmark", "Amicalola Falls State Park is the traditional starting gateway for northbound AT thru-hikers."),
            Claim("terrain", "The 8.5-mile Approach Trail from Amicalola Falls gains substantial elevation to reach Springer Mountain."),
            Claim("landmark", "Amicalola Falls at 729 feet is one of the tallest cascading waterfalls in the eastern United States."),
        ],
    },
    {
        "keys": ["hike inn", "the hike inn"],
        "state": "Georgia",
        "at_mile": None,
        "summary": "The Hike Inn is a backcountry eco-lodge accessible only by a 5-mile trail near Amicalola Falls.",
        "claims": [
            Claim("landmark", "The Hike Inn is a backcountry eco-lodge accessible only on foot via a 5-mile trail near Amicalola Falls."),
            Claim("terrain", "The Hike Inn sits within sight of the AT approach corridor through classic Blue Ridge hardwood forest."),
        ],
    },
    {
        "keys": ["stover creek shelter", "stover creek"],
        "state": "Georgia",
        "at_mile": 2.6,
        "summary": "Stover Creek Shelter (AT mile ~2.6) is one of the first shelter stops north of Springer Mountain.",
        "claims": [
            Claim("landmark", "Stover Creek Shelter at roughly AT mile 2.6 is among the first overnight shelters north of Springer Mountain."),
            Claim("terrain", "The Stover Creek area features a stream crossing and dense mixed forest typical of the Georgia Blue Ridge."),
        ],
    },
    {
        "keys": ["hawk mountain shelter", "hawk mountain"],
        "state": "Georgia",
        "at_mile": 8.1,
        "summary": "Hawk Mountain Shelter (AT mile ~8) is an early overnight stop in Georgia's Blue Ridge.",
        "claims": [
            Claim("landmark", "Hawk Mountain Shelter sits at roughly AT mile 8 from Springer Mountain in the Georgia Blue Ridge."),
            Claim("terrain", "The trail between Springer Mountain and Hawk Mountain traverses rocky ridgeline sections through hardwood forest."),
        ],
    },
    {
        "keys": ["gooch mountain shelter", "gooch mountain"],
        "state": "Georgia",
        "at_mile": 15.8,
        "summary": "Gooch Mountain Shelter (AT mile ~16) is a popular early multi-day destination for northbound hikers.",
        "claims": [
            Claim("landmark", "Gooch Mountain Shelter near AT mile 16 is a popular first multi-night destination for northbound thru-hikers."),
            Claim("terrain", "The trail from Hawk Mountain to Gooch Mountain crosses Justus Creek and climbs through mixed hardwood forest."),
            Claim("terrain", "The Gooch Mountain area receives heavy hiker traffic in early spring during thru-hiking season."),
        ],
    },
    {
        "keys": ["woody gap"],
        "state": "Georgia",
        "at_mile": 20.9,
        "summary": "Woody Gap (GA-60, AT mile ~21) is the first major road crossing northbound in Georgia.",
        "claims": [
            Claim("landmark", "Woody Gap at GA-60 provides a road crossing with a small picnic area and is a popular day-hiker trailhead."),
        ],
    },
    {
        "keys": ["blood mountain shelter", "blood mountain"],
        "state": "Georgia",
        "at_mile": 31.7,
        "summary": "Blood Mountain (4,458 ft) is the highest peak in Georgia on the AT, with a 1930s stone shelter.",
        "claims": [
            Claim("landmark", "Blood Mountain at 4,458 feet is the highest point on the Appalachian Trail in Georgia."),
            Claim("landmark", "The stone Blood Mountain Shelter dates to the 1930s CCC era and offers panoramic views from the summit."),
            Claim("history", "Blood Mountain takes its name from a Cherokee legend of a great battle fought on its slopes."),
        ],
    },
    {
        "keys": ["neels gap", "mountain crossings", "walasi-yi"],
        "state": "Georgia",
        "at_mile": 31.7,
        "nearest_town": "Blairsville, GA",
        "summary": "Neels Gap is the only point where the AT passes through a building — Mountain Crossings outfitter at Walasi-Yi.",
        "claims": [
            Claim("landmark", "Neels Gap at US-129 is unique as the only point where the Appalachian Trail passes through a building."),
            Claim("landmark", "Mountain Crossings at Walasi-Yi is a legendary AT outfitter where many hikers cull pack weight."),
        ],
    },
    {
        "keys": ["unicoi gap"],
        "state": "Georgia",
        "at_mile": 45.2,
        "nearest_town": "Helen, GA",
        "summary": "Unicoi Gap (GA-75) provides access to Helen, GA, a quirky Bavarian-themed mountain town.",
        "claims": [
            Claim("landmark", "Unicoi Gap at GA-75 is the nearest AT trailhead to Helen, Georgia's Bavarian-themed mountain town."),
        ],
    },
    {
        "keys": ["tray mountain"],
        "state": "Georgia",
        "at_mile": 56.7,
        "summary": "Tray Mountain (4,430 ft) is the second-highest peak in Georgia on the AT.",
        "claims": [
            Claim("terrain", "Tray Mountain at 4,430 feet is the second-highest peak on the AT in Georgia with open rocky summit views."),
        ],
    },
    {
        "keys": ["bly gap"],
        "state": "Georgia",
        "at_mile": 78.2,
        "summary": "Bly Gap marks the Georgia-North Carolina state line, the first state border northbound hikers cross.",
        "claims": [
            Claim("landmark", "Bly Gap marks the Georgia-North Carolina state line—the first state crossing celebrated by northbound thru-hikers."),
        ],
    },
    {
        "keys": ["standing indian"],
        "state": "North Carolina",
        "at_mile": 88.1,
        "summary": "Standing Indian Mountain (5,498 ft) is the highest peak south of the Smokies on the AT.",
        "claims": [
            Claim("landmark", "Standing Indian Mountain at 5,498 feet is the highest peak south of the Great Smokies on the AT."),
            Claim("terrain", "The Standing Indian area is known for its high balds and sweeping views of the southern Appalachians."),
        ],
    },
    {
        "keys": ["franklin"],
        "state": "North Carolina",
        "nearest_town": "Franklin, NC",
        "summary": "Franklin, NC is the first major trail town in North Carolina, offering full resupply and services.",
        "claims": [
            Claim("landmark", "Franklin, NC is a major trail town accessible from the AT via US-64, offering full resupply and hiker services."),
        ],
    },
    {
        "keys": ["wayah bald"],
        "state": "North Carolina",
        "at_mile": 109.6,
        "summary": "Wayah Bald (5,342 ft) features a restored 1930s stone fire tower with 360-degree views.",
        "claims": [
            Claim("landmark", "Wayah Bald at 5,342 feet features a restored 1930s stone fire tower with 360-degree mountain views."),
            Claim("terrain", "The open grassy bald atop Wayah offers clear-day views stretching to the Great Smoky Mountains."),
        ],
    },
    {
        "keys": ["nantahala outdoor center", "nantahala", "noc"],
        "state": "North Carolina",
        "at_mile": 135.8,
        "nearest_town": "Bryson City, NC",
        "summary": "The Nantahala Outdoor Center (NOC) at the Nantahala River gorge offers food, lodging, and gear.",
        "claims": [
            Claim("landmark", "The Nantahala Outdoor Center sits at the Nantahala River gorge and is a major AT resupply landmark."),
            Claim("terrain", "The climb out of the NOC is famously steep—over 3,000 feet to Swim Bald, one of the hardest single climbs in the South."),
        ],
    },
    {
        "keys": ["fontana dam", "fontana hilton"],
        "state": "North Carolina",
        "at_mile": 161.9,
        "summary": "Fontana Dam (480 ft tall) is crossed by the AT entering Great Smoky Mountains National Park.",
        "claims": [
            Claim("landmark", "Fontana Dam at 480 feet is the tallest dam east of the Mississippi River; the AT crosses it entering GSMNP."),
            Claim("landmark", "Fontana Dam Shelter is nicknamed the 'Fontana Hilton' for its spacious shower and laundry facilities."),
        ],
    },
    {
        "keys": ["clingmans dome", "clingman's dome"],
        "state": "Tennessee",
        "at_mile": 197.5,
        "summary": "Clingmans Dome (6,643 ft) is the highest point on the entire Appalachian Trail.",
        "claims": [
            Claim("landmark", "Clingmans Dome at 6,643 feet is the highest point on the entire Appalachian Trail."),
            Claim("landmark", "A concrete observation tower atop Clingmans Dome offers iconic views over Great Smoky Mountains NP."),
        ],
    },
    {
        "keys": ["davenport gap"],
        "state": "Tennessee",
        "at_mile": 231.5,
        "summary": "Davenport Gap marks the northern exit from Great Smoky Mountains National Park.",
        "claims": [
            Claim("landmark", "Davenport Gap at TN-32/NC-284 marks the northern exit from Great Smoky Mountains National Park."),
        ],
    },
    {
        "keys": ["hot springs"],
        "state": "North Carolina",
        "at_mile": 273.2,
        "nearest_town": "Hot Springs, NC",
        "summary": "Hot Springs, NC is a beloved trail town where the AT runs through Main Street past natural hot springs.",
        "claims": [
            Claim("landmark", "Hot Springs, NC is one of the few towns where the Appalachian Trail passes directly through Main Street."),
            Claim("landmark", "The natural hot spring spas in Hot Springs are a beloved thru-hiker destination for soaking tired muscles."),
        ],
    },
    {
        "keys": ["roan mountain", "roan highlands"],
        "state": "Tennessee",
        "at_mile": 373.0,
        "summary": "Roan Mountain's high balds above 6,000 feet feature some of the most spectacular ridge walking on the AT.",
        "claims": [
            Claim("terrain", "Roan Mountain's high balds above 6,000 feet offer some of the most dramatic open ridge walking on the AT."),
            Claim("terrain", "The Roan Highlands are famous for June rhododendron blooms and sweeping Appalachian views year-round."),
        ],
    },
    {
        "keys": ["damascus"],
        "state": "Virginia",
        "at_mile": 469.6,
        "nearest_town": "Damascus, VA",
        "summary": "Damascus, VA — 'Trail Town USA' — hosts Trail Days each May and is a beloved thru-hiker milestone.",
        "claims": [
            Claim("landmark", "Damascus, VA is known as 'Trail Town USA'; the AT runs directly through the center of town."),
            Claim("landmark", "Damascus hosts Trail Days each May, the largest annual gathering of Appalachian Trail hikers."),
        ],
    },
    {
        "keys": ["mcafee knob"],
        "state": "Virginia",
        "at_mile": 714.2,
        "summary": "McAfee Knob's overhanging rock ledge is the most photographed spot on the Appalachian Trail.",
        "claims": [
            Claim("landmark", "McAfee Knob's overhanging rock ledge is the single most photographed location on the entire AT."),
            Claim("terrain", "The view from McAfee Knob extends across the Catawba Valley and surrounding Virginia ridgelines."),
        ],
    },
    {
        "keys": ["harpers ferry"],
        "state": "West Virginia",
        "at_mile": 1023.2,
        "nearest_town": "Harpers Ferry, WV",
        "summary": "Harpers Ferry is the psychological midpoint of the AT and home to the Appalachian Trail Conservancy headquarters.",
        "claims": [
            Claim("landmark", "Harpers Ferry, WV is the psychological midpoint of the AT and headquarters of the Appalachian Trail Conservancy."),
            Claim("history", "Harpers Ferry's historic downtown is the site of John Brown's 1859 raid on the federal arsenal."),
        ],
    },
    {
        "keys": ["katahdin", "baxter peak"],
        "state": "Maine",
        "at_mile": 2190.0,
        "summary": "Mount Katahdin (5,267 ft) in Baxter State Park, Maine, is the northern terminus of the Appalachian Trail.",
        "claims": [
            Claim("landmark", "Mount Katahdin at 5,267 feet in Baxter State Park is the northern terminus of the Appalachian Trail."),
            Claim("landmark", "The summit sign at Baxter Peak on Katahdin marks the end—or beginning—of the 2,190-mile AT."),
        ],
    },
]

# General terrain facts by state (appended when a state match is found)
_STATE_TERRAIN: dict = {
    "Georgia": [
        Claim("terrain", "The Georgia AT traverses the southern Blue Ridge Mountains, crossing several 4,000-foot summits in ~76 miles."),
        Claim("terrain", "Georgia's AT features rocky ridgelines alternating with dense hardwood forest typical of the southern Appalachians."),
    ],
    "North Carolina": [
        Claim("terrain", "The North Carolina AT includes some of the highest peaks east of the Mississippi outside the Rockies."),
    ],
    "Tennessee": [
        Claim("terrain", "The Tennessee AT passes through Great Smoky Mountains National Park, the most visited national park in the US."),
    ],
    "Virginia": [
        Claim("terrain", "Virginia contains more AT miles than any other state—over 550—through the Blue Ridge and Allegheny Mountains."),
    ],
}


def _match_location(normalized: str):
    """Return the first knowledge entry whose any key is a substring match."""
    for entry in _LOCATION_KNOWLEDGE:
        for key in entry["keys"]:
            if key in normalized or normalized in key:
                return entry
    return None


def draft_section_facts(metadata) -> DraftFacts:
    """Generate rule-based draft facts for an AT journal entry.

    Combines endpoint landmark knowledge with mile-range segment guides.
    """
    from scripts.facts.location_resolver import normalize_name
    from scripts.facts.segment_guide import build_segment_description

    start = _get_attr(metadata, "start_location", "")
    dest = _get_attr(metadata, "destination", "")
    miles_hiked = float(_get_attr(metadata, "miles_hiked") or 0)
    trip_miles = float(_get_attr(metadata, "total_miles") or 0)

    start_norm = normalize_name(start) if start else ""
    dest_norm = normalize_name(dest) if dest else ""

    collected_claims: list = []
    summaries: list = []
    at_mile_start: Optional[float] = None
    at_mile_end: Optional[float] = None
    state: Optional[str] = None
    nearest_town: Optional[str] = None
    segment_name: Optional[str] = None
    region: Optional[str] = None

    for norm, is_start in [(start_norm, True), (dest_norm, False)]:
        entry = _match_location(norm)
        if entry:
            collected_claims.extend(entry.get("claims", []))
            summaries.append(entry.get("summary", ""))
            if entry.get("state"):
                state = entry["state"]
            if entry.get("nearest_town"):
                nearest_town = entry["nearest_town"]
            if entry.get("at_mile") is not None:
                if is_start:
                    at_mile_start = entry["at_mile"]
                else:
                    at_mile_end = entry["at_mile"]

    # Mile-range segment guide (primary narrative for the day's hike)
    seg_summary, seg_claims, seg_meta = build_segment_description(
        start, dest, miles_hiked, trip_miles
    )
    if seg_summary:
        summaries.insert(0, seg_summary)
        collected_claims = seg_claims + collected_claims
    if seg_meta:
        segment_name = seg_meta.get("segment_name") or segment_name
        region = seg_meta.get("region") or region
        if seg_meta.get("at_mile_start") is not None:
            at_mile_start = seg_meta["at_mile_start"]
        if seg_meta.get("at_mile_end") is not None:
            at_mile_end = seg_meta["at_mile_end"]
        if region and not state:
            state = region.split("/")[0].strip() if "/" in region else region

    # Add state terrain context when identified
    if state and state in _STATE_TERRAIN:
        collected_claims.extend(_STATE_TERRAIN[state])

    # Deduplicate claims by text
    seen: set = set()
    unique_claims: list = []
    for claim in collected_claims:
        if claim.text not in seen:
            seen.add(claim.text)
            unique_claims.append(claim)

    summary = " ".join(s for s in summaries if s)
    if not summary:
        summary = f"Trail section from {start} to {dest}." if start and dest else ""

    return DraftFacts(
        trail_section_summary=summary,
        claims=unique_claims,
        at_mile_start=at_mile_start,
        at_mile_end=at_mile_end,
        state=state,
        nearest_town=nearest_town,
        segment_name=segment_name,
        region=region,
    )
