#!/usr/bin/env python3
"""
Swift Travels - Daily Deal Fetcher
Runs via GitHub Actions to update data/deals.json with the cheapest flight.
"""

import os
import json
import time
from datetime import datetime, timedelta
import requests

# ---------- Configuration ----------
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    print("ERROR: RAPIDAPI_KEY environment variable not set")
    exit(1)

# Flight search parameters (from GitHub Secrets or defaults)
ORIGIN = os.environ.get("FLIGHT_ORIGIN", "LHR")
DESTINATION = os.environ.get("FLIGHT_DESTINATION", "CDG")
DEPART_DATE = os.environ.get("FLIGHT_DEPART_DATE")
if not DEPART_DATE:
    DEPART_DATE = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

CURRENCY = "USD"
LOCALE = "en-US"
MARKET = "US"
ADULTS = 1

BASE_URL = "https://skyscanner89.p.rapidapi.com"
HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "skyscanner89.p.rapidapi.com",
    "Content-Type": "application/json"
}

# ---------- Helper Functions ----------
def poll_until_complete(session_token: str, max_attempts: int = 12) -> dict:
    """Poll the Skyscanner API until results are ready."""
    poll_url = f"{BASE_URL}/flights/live/search/poll/{session_token}"
    for attempt in range(1, max_attempts + 1):
        time.sleep(2)
        resp = requests.post(poll_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        print(f"  Poll attempt {attempt}: {status}")
        if status == "RESULT_STATUS_COMPLETE":
            return data
    raise Exception(f"Polling timed out after {max_attempts} attempts")

def fetch_cheapest_flight() -> dict:
    """Search for flights and return the cheapest itinerary."""
    print(f"✈️  Searching {ORIGIN} → {DESTINATION} on {DEPART_DATE}")

    # Create search session
    create_payload = {
        "query": {
            "market": MARKET,
            "locale": LOCALE,
            "currency": CURRENCY,
            "queryLegs": [{
                "originPlaceId": {"iata": ORIGIN},
                "destinationPlaceId": {"iata": DESTINATION},
                "date": {
                    "year": int(DEPART_DATE[:4]),
                    "month": int(DEPART_DATE[5:7]),
                    "day": int(DEPART_DATE[8:10])
                }
            }],
            "adults": ADULTS,
            "cabinClass": "CABIN_CLASS_ECONOMY"
        }
    }

    resp = requests.post(
        f"{BASE_URL}/flights/live/search/create",
        headers=HEADERS,
        json=create_payload,
        timeout=30
    )
    resp.raise_for_status()
    session_token = resp.json().get("sessionToken")
    if not session_token:
        raise Exception("No session token returned")

    print(f"  Session created: {session_token[:20]}...")

    # Poll for results
    poll_data = poll_until_complete(session_token)

    # Extract cheapest flight
    itineraries = poll_data.get("content", {}).get("results", {}).get("itineraries", {})
    flights = []
    for bucket in itineraries.values():
        for item in bucket.get("items", []):
            price_info = item.get("price", {})
            price = float(price_info.get("amount", 999999))
            currency = price_info.get("unit", "USD")
            airline = item.get("legs", [{}])[0].get("carriers", [{}])[0].get("name", "Unknown")
            deeplink = item.get("deeplink", "")
            flights.append({
                "price": price,
                "currency": currency,
                "airline": airline,
                "deeplink": deeplink,
                "origin": ORIGIN,
                "destination": DESTINATION,
                "depart_date": DEPART_DATE
            })

    if not flights:
        raise Exception("No flights found")

    cheapest = min(flights, key=lambda x: x["price"])
    print(f"  ✅ Cheapest: {cheapest['price']:.2f} {cheapest['currency']} on {cheapest['airline']}")
    return cheapest

# ---------- Main ----------
def main():
    print("=" * 50)
    print("🛫 Swift Travels – Fetching Daily Deals")
    print("=" * 50)

    deals = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "flights": None,
        "hotels": None,   # Placeholder for future expansion
        "cars": None      # Placeholder for future expansion
    }

    try:
        deals["flights"] = fetch_cheapest_flight()
    except Exception as e:
        print(f"❌ Flight search failed: {e}")
        exit(1)

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    # Write JSON file
    output_path = os.path.join("data", "deals.json")
    with open(output_path, "w") as f:
        json.dump(deals, f, indent=2)

    print(f"\n✅ Deals saved to {output_path}")

if __name__ == "__main__":
    main()
