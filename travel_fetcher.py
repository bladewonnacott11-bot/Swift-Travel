import os
import json
import time
import sys
import requests
from datetime import datetime, timedelta

# ------------------- Configuration -------------------
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    print("ERROR: RAPIDAPI_KEY is not set.")
    sys.exit(1)

FLIGHT_ORIGIN = os.getenv("FLIGHT_ORIGIN", "LHR")
FLIGHT_DESTINATION = os.getenv("FLIGHT_DESTINATION", "CDG")
DEPART_DATE = os.getenv("FLIGHT_DEPART_DATE", "")
CURRENCY = os.getenv("CURRENCY", "USD")
LOCALE = os.getenv("LOCALE", "en-US")
MARKET = os.getenv("MARKET", "US")
ADULTS = int(os.getenv("ADULTS", "1"))

HOTEL_CITY = os.getenv("HOTEL_CITY", "Paris")
CHECKIN_DATE = os.getenv("CHECKIN_DATE", "")
CHECKOUT_DATE = os.getenv("CHECKOUT_DATE", "")
ROOMS = int(os.getenv("ROOMS", "1"))
GUESTS = int(os.getenv("GUESTS", "2"))

CAR_PICKUP_PLACE = os.getenv("CAR_PICKUP_PLACE", "CDG")
CAR_DROPOFF_PLACE = os.getenv("CAR_DROPOFF_PLACE", "CDG")
CAR_PICKUP_DATE = os.getenv("CAR_PICKUP_DATE", "")
CAR_DROPOFF_DATE = os.getenv("CAR_DROPOFF_DATE", "")
DRIVER_AGE = int(os.getenv("DRIVER_AGE", "30"))

# Set default dates if not provided
if not DEPART_DATE:
    DEPART_DATE = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
if not CHECKIN_DATE:
    CHECKIN_DATE = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
if not CHECKOUT_DATE:
    CHECKOUT_DATE = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d")
if not CAR_PICKUP_DATE:
    CAR_PICKUP_DATE = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT10:00:00")
if not CAR_DROPOFF_DATE:
    CAR_DROPOFF_DATE = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%dT10:00:00")

BASE_URL = "https://skyscanner89.p.rapidapi.com"
HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "skyscanner89.p.rapidapi.com",
    "Content-Type": "application/json"
}

# ------------------- Helpers -------------------
def make_request(method, endpoint, json_data=None):
    url = f"{BASE_URL}{endpoint}"
    print(f"  → {method} {endpoint}")
    if method.upper() == "POST":
        resp = requests.post(url, headers=HEADERS, json=json_data, timeout=30)
    else:
        resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()

def poll_until_complete(endpoint, session_token, max_attempts=10):
    poll_url = f"{endpoint}/{session_token}"
    for attempt in range(max_attempts):
        time.sleep(2)
        data = make_request("POST", poll_url)
        status = data.get("status")
        if status == "RESULT_STATUS_COMPLETE":
            return data
        print(f"    Polling {endpoint.split('/')[-2]} ({attempt+1}/{max_attempts})...")
    return None

# ------------------- Flights -------------------
def fetch_cheapest_flight():
    print(f"\n✈️  Searching flights: {FLIGHT_ORIGIN} → {FLIGHT_DESTINATION} on {DEPART_DATE}")
    payload = {
        "query": {
            "market": MARKET,
            "locale": LOCALE,
            "currency": CURRENCY,
            "queryLegs": [{
                "originPlaceId": {"iata": FLIGHT_ORIGIN},
                "destinationPlaceId": {"iata": FLIGHT_DESTINATION},
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
    try:
        create_resp = make_request("POST", "/flights/live/search/create", payload)
        token = create_resp.get("sessionToken")
        if not token:
            print("    ❌ No session token")
            return None

        data = poll_until_complete("/flights/live/search/poll", token)
        if not data:
            print("    ❌ Polling timeout")
            return None

        itineraries = data.get("content", {}).get("results", {}).get("itineraries", {})
        flights = []
        for bucket in itineraries.values():
            for item in bucket.get("items", []):
                price = float(item.get("price", {}).get("amount", 999999))
                currency = item.get("price", {}).get("unit", "USD")
                airline = item.get("legs", [{}])[0].get("carriers", [{}])[0].get("name", "Unknown")
                deeplink = item.get("deeplink", "")
                flights.append({"price": price, "currency": currency, "airline": airline, "deeplink": deeplink})
        if flights:
            cheapest = min(flights, key=lambda x: x["price"])
            cheapest["origin"] = FLIGHT_ORIGIN
            cheapest["destination"] = FLIGHT_DESTINATION
            cheapest["depart_date"] = DEPART_DATE
            print(f"    ✅ Found: {cheapest['price']:.2f} {cheapest['currency']} on {cheapest['airline']}")
            return cheapest
        else:
            print("    ⚠️ No flight itineraries found")
    except Exception as e:
        print(f"    ❌ Error: {e}")
    return None

# ------------------- Hotels -------------------
def fetch_cheapest_hotel():
    print(f"\n🏨 Searching hotels in {HOTEL_CITY} ({CHECKIN_DATE} to {CHECKOUT_DATE})")
    payload = {
        "query": {
            "market": MARKET,
            "locale": LOCALE,
            "currency": CURRENCY,
            "query": {
                "place": {"name": HOTEL_CITY},
                "checkin": CHECKIN_DATE,
                "checkout": CHECKOUT_DATE,
                "rooms": ROOMS,
                "adults": GUESTS
            }
        }
    }
    try:
        create_resp = make_request("POST", "/hotels/live/search/create", payload)
        token = create_resp.get("sessionToken")
        if not token:
            print("    ❌ No session token")
            return None

        data = poll_until_complete("/hotels/live/search/poll", token)
        if not data:
            print("    ❌ Polling timeout")
            return None

        hotels = data.get("content", {}).get("results", {}).get("hotels", [])
        if not hotels:
            print("    ⚠️ No hotels found")
            return None
        cheapest = min(hotels, key=lambda h: float(h.get("price", {}).get("total", 999999)))
        price_info = cheapest.get("price", {})
        result = {
            "name": cheapest.get("name", "Unknown Hotel"),
            "price": float(price_info.get("total", 999999)),
            "currency": price_info.get("currency", CURRENCY),
            "deeplink": cheapest.get("deeplink", ""),
            "city": HOTEL_CITY,
            "checkin": CHECKIN_DATE,
            "checkout": CHECKOUT_DATE
        }
        print(f"    ✅ Found: {result['price']:.2f} {result['currency']} at {result['name']}")
        return result
    except Exception as e:
        print(f"    ❌ Error: {e}")
    return None

# ------------------- Cars -------------------
def fetch_cheapest_car():
    print(f"\n🚗 Searching car hire: {CAR_PICKUP_PLACE} from {CAR_PICKUP_DATE} to {CAR_DROPOFF_DATE}")
    payload = {
        "query": {
            "market": MARKET,
            "locale": LOCALE,
            "currency": CURRENCY,
            "pickupPlace": {"iata": CAR_PICKUP_PLACE},
            "dropoffPlace": {"iata": CAR_DROPOFF_PLACE},
            "pickupDateTime": CAR_PICKUP_DATE,
            "dropoffDateTime": CAR_DROPOFF_DATE,
            "driverAge": DRIVER_AGE
        }
    }
    try:
        create_resp = make_request("POST", "/carhire/live/search/create", payload)
        token = create_resp.get("sessionToken")
        if not token:
            print("    ❌ No session token")
            return None

        data = poll_until_complete("/carhire/live/search/poll", token)
        if not data:
            print("    ❌ Polling timeout")
            return None

        cars = data.get("content", {}).get("results", {}).get("cars", [])
        if not cars:
            print("    ⚠️ No cars found")
            return None
        cheapest = min(cars, key=lambda c: float(c.get("price", {}).get("total", 999999)))
        price_info = cheapest.get("price", {})
        supplier = cheapest.get("supplier", {}).get("name", "Unknown")
        vehicle = cheapest.get("vehicle", {}).get("name", "Standard")
        result = {
            "supplier": supplier,
            "vehicle": vehicle,
            "price": float(price_info.get("total", 999999)),
            "currency": price_info.get("currency", CURRENCY),
            "deeplink": cheapest.get("deeplink", ""),
            "pickup": CAR_PICKUP_PLACE,
            "dropoff": CAR_DROPOFF_PLACE,
            "pickup_date": CAR_PICKUP_DATE[:10],
            "dropoff_date": CAR_DROPOFF_DATE[:10]
        }
        print(f"    ✅ Found: {result['price']:.2f} {result['currency']} from {supplier} ({vehicle})")
        return result
    except Exception as e:
        print(f"    ❌ Error: {e}")
    return None

# ------------------- Main -------------------
def main():
    print("=" * 50)
    print("🛫 Swift Travels – Fetching Deals")
    print("=" * 50)

    deals = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "flights": None,
        "hotels": None,
        "cars": None
    }

    # Flights (required)
    deals["flights"] = fetch_cheapest_flight()
    if not deals["flights"]:
        print("\n❌ Failed to fetch flight deals. Exiting.")
        sys.exit(1)

    # Hotels (optional – skip if fails)
    deals["hotels"] = fetch_cheapest_hotel()

    # Cars (optional – skip if fails)
    deals["cars"] = fetch_cheapest_car()

    # Save
    os.makedirs("data", exist_ok=True)
    with open("data/deals.json", "w") as f:
        json.dump(deals, f, indent=2)

    print("\n✅ Deals saved to data/deals.json")

if __name__ == "__main__":
    main()
