"""
Discover cafes in a neighbourhood AND download their photos.
Outputs:
    cafes.csv          - one row per cafe
    menus/<place_id>/  - photos for each cafe

Usage:
    python discover_and_fetch.py "Mount Pleasant" 49.2647 -123.1009 1500
    # args: neighbourhood_name, lat, lng, radius_meters
"""
import csv
import os
import sys
import time
from pathlib import Path

import requests

API_KEY = os.environ["GOOGLE_PLACES_API_KEY"]
NEARBY_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

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

KEYWORDS = ["matcha", "cafe", "coffee", "tea"]

CHAIN_BLOCKLIST = {
    "mcdonald's", "mcdonalds", "starbucks", "tim hortons",
    "blenz", "waves coffee", "a&w", "subway",
    "second cup", "7-eleven", "shell", "esso",
}


def is_chain(name: str) -> bool:
    n = name.lower().strip()
    return any(chain in n for chain in CHAIN_BLOCKLIST)


def search_nearby(lat, lng, radius, keyword):
    body = {
        "includedTypes": ["cafe", "coffee_shop"],
        "maxResultCount": 20,
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
    resp = requests.post(NEARBY_ENDPOINT, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("places", [])


def normalize(place, neighbourhood):
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


def fetch_photos(place_id: str, max_photos: int = 10):
    """Download up to max_photos for one place into menus/<place_id>/."""
    out_dir = Path("menus") / place_id
    
    # Skip if we've already fetched photos for this place
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"    skipping (already have photos)")
        return

    # Get the list of photos attached to this place
    details_url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "photos",
    }
    resp = requests.get(details_url, headers=headers, timeout=30)
    resp.raise_for_status()
    photos = resp.json().get("photos", [])

    if not photos:
        print(f"    no photos available")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    for i, photo in enumerate(photos[:max_photos]):
        photo_name = photo["name"]
        photo_url = f"https://places.googleapis.com/v1/{photo_name}/media"
        params = {"key": API_KEY, "maxWidthPx": 1600}
        r = requests.get(photo_url, params=params, timeout=30)
        r.raise_for_status()
        out_path = out_dir / f"photo_{i:02d}.jpg"
        out_path.write_bytes(r.content)

    print(f"    downloaded {min(len(photos), max_photos)} photo(s)")


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)

    neighbourhood = sys.argv[1]
    lat = float(sys.argv[2])
    lng = float(sys.argv[3])
    radius = float(sys.argv[4])

    seen = {}
    skipped_chains = 0

    # --- Phase 1: discover cafes ---
    print("=" * 50)
    print("Phase 1: discovering cafes")
    print("=" * 50)
    for kw in KEYWORDS:
        print(f"Searching '{kw}'...")
        try:
            places = search_nearby(lat, lng, radius, kw)
        except requests.HTTPError as e:
            print(f"  ERROR: {e.response.status_code} {e.response.text}")
            continue

        for p in places:
            if p.get("businessStatus") and p["businessStatus"] != "OPERATIONAL":
                continue
            cafe = normalize(p, neighbourhood)
            if is_chain(cafe["name"]):
                skipped_chains += 1
                continue
            seen[cafe["place_id"]] = cafe

        print(f"  got {len(places)} (total unique: {len(seen)})")
        time.sleep(0.5)

    if not seen:
        print("\nNo cafes found.")
        return

    # Write cafes.csv
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

    # --- Phase 2: fetch photos ---
    print()
    print("=" * 50)
    print("Phase 2: fetching photos")
    print("=" * 50)
    for cafe in seen.values():
        print(f"\n{cafe['name']} ({cafe['place_id']}):")
        try:
            fetch_photos(cafe["place_id"])
        except requests.HTTPError as e:
            print(f"    ERROR: {e.response.status_code} {e.response.text}")
        time.sleep(0.3)

    print("\nDone.")


if __name__ == "__main__":
    main()
