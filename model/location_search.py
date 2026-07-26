"""
location_search.py
--------------------
Village/district/state autocomplete via Photon (https://photon.komoot.io),
an OpenStreetMap-based geocoder built for type-ahead search. Unlike
Nominatim's /search endpoint, Photon matches partial words (e.g. "luckno"
-> "Lucknow"), which is what an autocomplete box needs. Results are
restricted to India through a bounding box.

If the request fails (no internet in this environment, rate limited, etc.)
it returns an empty result list with a note -- callers should treat this
gracefully rather than erroring out.
"""

try:
    import requests
except ImportError:
    requests = None

PHOTON_URL = "https://photon.komoot.io/api/"
HEADERS = {"User-Agent": "KrishiMitra-ISRO-Hackathon/1.0"}
# minLon, minLat, maxLon, maxLat -- roughly the Indian subcontinent, so
# suggestions stay relevant to farmers using the app.
INDIA_BBOX = "68.0,6.0,97.5,37.5"


def _label(props):
    """Build a human-readable "Place, District, State, Country" string,
    skipping missing/duplicate parts."""
    parts = []
    for key in ("name", "city", "county", "state", "country"):
        val = props.get(key)
        if val and val not in parts:
            parts.append(val)
    return ", ".join(parts)


def search_location(query, limit=6):
    if not query or requests is None:
        return {"results": [], "note": "query missing ya requests library available nahi hai"}
    try:
        resp = requests.get(PHOTON_URL, params={
            "q": query, "lang": "en", "limit": limit, "bbox": INDIA_BBOX,
        }, headers=HEADERS, timeout=5)
        if resp.status_code != 200:
            return {"results": [], "note": f"Photon status {resp.status_code}"}
        features = resp.json().get("features", [])
        results = []
        for feat in features:
            props = feat.get("properties", {})
            coords = (feat.get("geometry") or {}).get("coordinates") or []
            if len(coords) < 2:
                continue
            name = props.get("name")
            results.append({
                "display_name": _label(props),
                "lat": float(coords[1]), "lon": float(coords[0]),
                "village": name or props.get("city"),
                "district": props.get("county") or props.get("district") or props.get("city"),
                "state": props.get("state"),
            })
        return {"results": results, "note": None}
    except Exception as e:
        return {"results": [], "note": f"Location search fail ho gayi: {e}"}