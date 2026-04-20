# api/search.py
import os
import json
import time
import requests
from datetime import datetime
from http.server import BaseHTTPRequestHandler

# CORS headers (allow requests from your frontend)
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
BASE_URL = "https://skyscanner89.p.rapidapi.com"
HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "skyscanner89.p.rapidapi.com",
    "Content-Type": "application/json"
}

def poll_until_complete(endpoint, session_token, max_attempts=10):
    poll_url = f"{BASE_URL}{endpoint}/{session_token}"
    for _ in range(max_attempts):
        time.sleep(2)
        resp = requests.post(poll_url, headers=HEADERS)
        data = resp.json()
        if data.get("status") == "RESULT_STATUS_COMPLETE":
            return data
    return None

def search_flight(origin, destination, depart_date, currency, locale, market, adults):
    payload = {
        "query": {
            "market": market,
            "locale": locale,
            "currency": currency,
            "queryLegs": [{
                "originPlaceId": {"iata": origin},
                "destinationPlaceId": {"iata": destination},
                "date": {
                    "year": int(depart_date[:4]),
                    "month": int(depart_date[5:7]),
                    "day": int(depart_date[8:10])
                }
            }],
            "adults": adults,
            "cabinClass": "CABIN_CLASS_ECONOMY"
        }
    }
    # Create session
    resp = requests.post(f"{BASE_URL}/flights/live/search/create", headers=HEADERS, json=payload)
    token = resp.json().get("sessionToken")
    if not token:
        return None
    data = poll_until_complete("/flights/live/search/poll", token)
    if not data:
        return None
    # Extract cheapest
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
        cheapest["origin"] = origin
        cheapest["destination"] = destination
        cheapest["depart_date"] = depart_date
        return cheapest
    return None

def handler(request, response):
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response.status_code = 204
        for key, value in CORS_HEADERS.items():
            response.headers[key] = value
        return response

    if request.method != "POST":
        response.status_code = 405
        response.body = json.dumps({"error": "Method not allowed"})
        return response

    try:
        body = json.loads(request.body)
        search_type = body.get("type", "flight")

        if search_type == "flight":
            result = search_flight(
                origin=body["origin"],
                destination=body["destination"],
                depart_date=body["depart_date"],
                currency=body.get("currency", "USD"),
                locale=body.get("locale", "en-US"),
                market=body.get("market", "US"),
                adults=int(body.get("adults", 1))
            )
        else:
            # For simplicity, we'll implement only flight search now.
            # Hotel and car can be added later following the same pattern.
            result = None

        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        for key, value in CORS_HEADERS.items():
            response.headers[key] = value
        response.body = json.dumps(result if result else {"error": "No results found"})

    except Exception as e:
        response.status_code = 500
        response.body = json.dumps({"error": str(e)})

    return response
