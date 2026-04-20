"""
Vercel Serverless Function – Flight Search via Skyscanner RapidAPI
Endpoint: POST /api/search
Expected JSON body:
{
    "origin": "LHR",
    "destination": "CDG",
    "depart_date": "2026-06-15",
    "adults": 1,
    "currency": "USD",
    "cabin": "ECONOMY",
    "locale": "en-US",
    "market": "US"
}
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import time
from typing import Dict, Any, Optional

import requests

# ---------- Configuration ----------
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
BASE_URL = "https://skyscanner89.p.rapidapi.com"
HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "skyscanner89.p.rapidapi.com",
    "Content-Type": "application/json"
}
MAX_POLL_ATTEMPTS = 12
POLL_DELAY_SECONDS = 2

# ---------- Helper Functions ----------
def log_error(message: str) -> None:
    """Write error message to stderr (visible in Vercel logs)."""
    print(f"[ERROR] {message}", file=sys.stderr)

def log_info(message: str) -> None:
    """Write info message to stdout (visible in Vercel logs)."""
    print(f"[INFO] {message}", file=sys.stdout)

def validate_request(data: Dict[str, Any]) -> Optional[str]:
    """Check required fields. Returns error message or None if valid."""
    required = ["origin", "destination", "depart_date"]
    for field in required:
        if field not in data:
            return f"Missing required field: {field}"
    # Validate date format
    depart_date = data["depart_date"]
    try:
        year, month, day = map(int, depart_date.split("-"))
        if not (2024 <= year <= 2027 and 1 <= month <= 12 and 1 <= day <= 31):
            return "Invalid date format or out of range (use YYYY-MM-DD)"
    except ValueError:
        return "Invalid date format (use YYYY-MM-DD)"
    # Validate IATA codes
    if not (data["origin"].isalpha() and len(data["origin"]) == 3):
        return "Origin must be a 3-letter IATA code"
    if not (data["destination"].isalpha() and len(data["destination"]) == 3):
        return "Destination must be a 3-letter IATA code"
    return None

def search_flight(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform flight search via Skyscanner RapidAPI.
    Raises Exception on failure; returns cheapest flight dict.
    """
    if not RAPIDAPI_KEY:
        raise Exception("RAPIDAPI_KEY environment variable not set")

    origin = data["origin"].upper()
    destination = data["destination"].upper()
    depart_date = data["depart_date"]
    currency = data.get("currency", "USD")
    locale = data.get("locale", "en-US")
    market = data.get("market", "US")
    adults = int(data.get("adults", 1))

    log_info(f"Searching {origin} → {destination} on {depart_date}")

    # ---------- Step 1: Create search session ----------
    create_payload = {
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

    try:
        resp = requests.post(
            f"{BASE_URL}/flights/live/search/create",
            headers=HEADERS,
            json=create_payload,
            timeout=30
        )
        resp.raise_for_status()
        session_token = resp.json().get("sessionToken")
        if not session_token:
            raise Exception("No session token returned from Skyscanner")
        log_info(f"Session created: {session_token[:20]}...")
    except requests.exceptions.RequestException as e:
        log_error(f"Create session failed: {e}")
        raise Exception(f"Skyscanner API error: {e}")

    # ---------- Step 2: Poll for results ----------
    poll_url = f"{BASE_URL}/flights/live/search/poll/{session_token}"
    poll_data = None

    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        time.sleep(POLL_DELAY_SECONDS)
        try:
            poll_resp = requests.post(poll_url, headers=HEADERS, timeout=30)
            poll_resp.raise_for_status()
            poll_data = poll_resp.json()
            status = poll_data.get("status")
            log_info(f"Poll attempt {attempt}: {status}")
            if status == "RESULT_STATUS_COMPLETE":
                break
        except Exception as e:
            log_error(f"Poll attempt {attempt} error: {e}")
            if attempt == MAX_POLL_ATTEMPTS:
                raise Exception(f"Polling failed after {MAX_POLL_ATTEMPTS} attempts: {e}")
    else:
        raise Exception(f"Polling timeout after {MAX_POLL_ATTEMPTS} attempts")

    if not poll_data:
        raise Exception("No data received from polling")

    # ---------- Step 3: Extract cheapest flight ----------
    itineraries = poll_data.get("content", {}).get("results", {}).get("itineraries", {})
    flights = []

    for bucket_id, bucket in itineraries.items():
        for item in bucket.get("items", []):
            try:
                price_info = item.get("price", {})
                price = float(price_info.get("amount", 999999))
                curr = price_info.get("unit", "USD")
                legs = item.get("legs", [])
                airline = "Unknown"
                if legs and legs[0].get("carriers"):
                    airline = legs[0]["carriers"][0].get("name", "Unknown")
                deeplink = item.get("deeplink", "")

                flights.append({
                    "price": price,
                    "currency": curr,
                    "airline": airline,
                    "deeplink": deeplink,
                    "origin": origin,
                    "destination": destination,
                    "depart_date": depart_date
                })
            except Exception as e:
                log_error(f"Error parsing flight item: {e}")
                continue

    if not flights:
        raise Exception("No flights found for this route and date")

    cheapest = min(flights, key=lambda x: x["price"])
    log_info(f"Cheapest flight: {cheapest['price']:.2f} {cheapest['currency']} on {cheapest['airline']}")
    return cheapest

# ---------- Vercel Handler Class ----------
class handler(BaseHTTPRequestHandler):
    """Vercel Python serverless handler."""

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        """Handle flight search POST requests."""
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length else b''

        # Parse JSON
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON format")
            return

        # Validate request
        validation_error = validate_request(data)
        if validation_error:
            self._send_error(400, validation_error)
            return

        # Perform search
        try:
            result = search_flight(data)
            self._send_json(200, result)
        except Exception as e:
            log_error(f"Search failed: {e}")
            self._send_error(500, str(e))

    def _send_cors_headers(self):
        """Add CORS headers to response."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        """Send JSON response with CORS headers."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status_code: int, message: str):
        """Send error response."""
        self._send_json(status_code, {"error": message})
