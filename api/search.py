# api/search.py
from http.server import BaseHTTPRequestHandler
import json
import os
import time
import requests
import sys

# RapidAPI configuration
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
BASE_URL = "https://skyscanner89.p.rapidapi.com"
HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "skyscanner89.p.rapidapi.com",
    "Content-Type": "application/json"
}

class handler(BaseHTTPRequestHandler):
    """Vercel Python serverless handler for flight search."""

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Handle POST requests for flight search."""
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length else b''

        # Parse JSON
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON format")
            return

        # Validate required fields
        required_fields = ['origin', 'destination', 'depart_date']
        for field in required_fields:
            if field not in data:
                self._send_error(400, f"Missing required field: {field}")
                return

        # Perform search
        try:
            result = self._search_flight(data)
            self._send_json(200, result)
        except Exception as e:
            print(f"Search error: {str(e)}", file=sys.stderr)
            self._send_error(500, f"Search failed: {str(e)}")

    def _send_json(self, status_code, data):
        """Send JSON response with CORS headers."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status_code, message):
        """Send error response."""
        self._send_json(status_code, {"error": message})

    def _search_flight(self, data):
        """Query Skyscanner API and return cheapest flight."""
        if not RAPIDAPI_KEY:
            raise Exception("RAPIDAPI_KEY environment variable not set")

        origin = data['origin'].upper()
        destination = data['destination'].upper()
        depart_date = data['depart_date']
        currency = data.get('currency', 'USD')
        locale = data.get('locale', 'en-US')
        market = data.get('market', 'US')
        adults = int(data.get('adults', 1))

        # Create search session
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

        # Step 1: Create session
        create_resp = requests.post(
            f"{BASE_URL}/flights/live/search/create",
            headers=HEADERS,
            json=create_payload,
            timeout=30
        )
        create_resp.raise_for_status()
        session_token = create_resp.json().get("sessionToken")
        if not session_token:
            raise Exception("No session token returned from Skyscanner")

        # Step 2: Poll for results (max 10 attempts, 2s delay)
        poll_url = f"{BASE_URL}/flights/live/search/poll/{session_token}"
        for attempt in range(1, 11):
            time.sleep(2)
            poll_resp = requests.post(poll_url, headers=HEADERS, timeout=30)
            poll_resp.raise_for_status()
            poll_data = poll_resp.json()
            status = poll_data.get("status")
            if status == "RESULT_STATUS_COMPLETE":
                break
            if attempt == 10:
                raise Exception("Search timed out after 10 attempts")

        # Step 3: Extract cheapest flight
        itineraries = poll_data.get("content", {}).get("results", {}).get("itineraries", {})
        flights = []
        for bucket in itineraries.values():
            for item in bucket.get("items", []):
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

        if not flights:
            raise Exception("No flights found for this route")

        cheapest = min(flights, key=lambda x: x["price"])
        return cheapest
