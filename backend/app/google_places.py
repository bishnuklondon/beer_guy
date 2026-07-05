import json
from typing import Any, Dict, List

import requests

from .config import GOOGLE_PLACES_API_KEY


def fetch_pub_records_from_google(
    district_post_code: str,
    district_name: str,
    latitude: float,
    longitude: float,
    limit: int,
) -> List[Dict[str, Any]]:
    if not GOOGLE_PLACES_API_KEY:
        raise ValueError("GOOGLE_PLACES_API_KEY is not configured")

    query_text = f"pubs near {district_name or district_post_code}"
    query_text = query_text.replace("-", "_")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.websiteUri,places.googleMapsUri,places.rating",
    }
    body = {"textQuery": query_text, "includedType": "bar"}

    response = requests.post(
        "https://places.googleapis.com/v1/places:searchText",
        headers=headers,
        data=json.dumps(body),
        timeout=60,
    )
    response.raise_for_status()

    payload = response.json()
    if payload.get("error"):
        error = payload["error"]
        raise RuntimeError(f"Google Places API error: {error.get('status')} - {error.get('message', '')}")

    places = payload.get("places", [])
    if not places and "results" in payload:
        places = payload.get("results", [])

    records: List[Dict[str, Any]] = []
    for item in places[:limit]:
        display_name = item.get("displayName") or item.get("name") or {}
        name = display_name.get("text") if isinstance(display_name, dict) else display_name or ""
        rating = item.get("rating") if item.get("rating") is not None else 0.0
        website_link = item.get("websiteUri") or item.get("website") or item.get("url") or ""
        googleMaps_link = item.get("googleMapsUri") or item.get("mapsLink") or ""
        address = item.get("formattedAddress") or item.get("vicinity") or item.get("formatted_address") or ""
        location = item.get("location") or item.get("geometry", {}).get("location", {})
        lat = location.get("latitude") if isinstance(location, dict) else None
        lng = location.get("longitude") if isinstance(location, dict) else None
        if lat is None and isinstance(location, dict):
            lat = location.get("lat")
            lng = location.get("lng")

        records.append(
            {
                "id": item.get("place_id") or f"{district_post_code.lower()}-{len(records) + 1}",
                "name": name or "",
                "address": address,
                "rating": rating,
                "district_post_code": district_post_code.upper(),
                "district_name": district_name or "",
                "geo_location": f"{lat},{lng}",
                "website_link": website_link,
                "googleMaps_link": googleMaps_link,
                "beverage_options": "",
            }
        )
    return records
