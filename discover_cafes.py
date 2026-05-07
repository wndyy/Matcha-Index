"""
Discover cafes in a given neighbourhood using Google Places API (New).
Outputs: cafes.csv with one row per cafe (chains excluded).

Usage:
    python discover_cafes.py "Mount Pleasant" 49.2647 -123.1009 1500
    # args: neighbourhood_name, lat, lng, radius_meters
"""
import csv
import os
import sys
import time
from pathlib import Path

import requests

API_KEY = os.environ["GOOGLE_PLACES_API_KEY"]
ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

# Fields we want back. Each field has a cost tier; this set stays in the
# cheaper "Pro" tier. See: developers.google.com/maps/documentation/places/web-service/nearby-search
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.websiteUri",
    "places.googleMapsUri",
    "places.primaryType",
    "places.businessStatus",
])

# Search keywords. We do separate calls because Places caps results at 20 per
# call and 'cafe' alone misses tea-focused spots.
KEYWORDS = ["matcha", "cafe", "coffee", "tea"]

# Chain stores to exclude. Lowercase, substring match against cafe name.
# Add to this list as you find more chains in your data.
CHAIN_BLOCKLIST = {
    "mcdonald's",
    "mcdonalds",
    "starbucks",
    "tim hortons",
    "blenz",
    "waves coffee",
    "a&w",
    "subway",
    "second cup",
    "7-eleven",
    "shell",
    "esso",
}


def is_chain(name: str) -> bool:
    """True if cafe name matches a known chain."""
    n = name.lower().strip()
    return any(chain in n for chain in CHAIN_BLOCKLIST)


def search_nearby(lat: float, lng: float, radius: float, keyword: str) -> list[dict]:
    """Single Places API Nearby Search call."""
    body = {
        "includedTypes": ["cafe", "coffee_shop"],
        "maxResultCount": 20,  # API hard cap
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius,
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    resp = requests.post(ENDPOINT, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("places", [])


def normalize(place: dict, neighbourhood: str) -> dict:
    """Flatten a Places API response into a CSV-friendly dict."""
    return {
        "place_id": place["id"],
        "name": place.get("displayName", {}).get("text", ""),
        "address": place.get("formattedAddress", ""),
        "lat": place.get("location", {}).get("latitude"),
        "lng": place.get("location", {}).get("longitude"),
        "website": place.get("websiteUri", ""),
        "google_maps_url": place.get("googleMapsUri", ""),
        "primary_type": place.get("primaryType", ""),
        "business_status": place.get("businessStatus", ""),
        "neighbourhood": neighbourhood,
    }


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)

    neighbourhood = sys.argv[1]
    lat = float(sys.argv[2])
    lng = float(sys.argv[3])
    radius = float(sys.argv[4])

    seen: dict[str, dict] = {}  # place_id -> normalized cafe
    skipped_chains = 0

    for kw in KEYWORDS:
        print(f"Searching '{kw}'...")
        try:
            places = search_nearby(lat, lng, radius, kw)
        except requests.HTTPError as e:
            print(f"  ERROR: {e.response.status_code} {e.response.text}")
            continue

        for p in places:
            if p.get("businessStatus") and p["businessStatus"] != "OPERATIONAL":
                continue  # skip closed/temporarily closed
            cafe = normalize(p, neighbourhood)
            if is_chain(cafe["name"]):
                skipped_chains += 1
                continue  # skip chains
            seen[cafe["place_id"]] = cafe

        print(f"  got {len(places)} (total unique: {len(seen)})")
        time.sleep(0.5)  # be nice

    if not seen:
        print("\nNo cafes found.")
        return

    out_path = Path("cafes.csv")
    write_header = not out_path.exists()
    with out_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(next(iter(seen.values())).keys()))
        if write_header:
            writer.writeheader()
        for cafe in seen.values():
            writer.writerow(cafe)

    print(f"\nWrote {len(seen)} cafes to {out_path.resolve()}")
    if skipped_chains:
        print(f"Skipped {skipped_chains} chain results.")


if __name__ == "__main__":
    main()
