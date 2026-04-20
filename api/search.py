from http.server import BaseHTTPRequestHandler
import json
import os
import time
import requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body)
        except:
            self._send_error(400, "Invalid JSON")
            return

        required = ['origin', 'destination', 'depart_date']
        for field in required:
            if field not in data:
                self._send_error(400, f"Missing field: {field}")
                return

        try:
            result = self._search_flight(data)
            self._send_json(200, result)
        except Exception as e:
            self._send_error(500, str(e))

    def _search_flight(self, data):
        if not RAPIDAPI_KEY:
            raise Exception("API key not configured")

        origin = data['origin'].upper()
        destination = data['destination'].upper()
        depart_date = data['depart_date']
        currency = data.get('currency', 'USD')
        locale = data.get('locale', 'en-US')
        market = data.get('market', 'US')
        adults = int(data.get('adults', 1))

        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "skyscanner89.p.rapidapi.com",
            "Content-Type": "application/json"
        }

        # Create session
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

        resp = requests.post(
            "https://skyscanner89.p.rapidapi.com/flights/live/search/create",
            headers=headers,
            json=create_payload,
            timeout=30
        )
        resp.raise_for_status()
        token = resp.json().get("sessionToken")
        if not token:
            raise Exception("No session token")

        # Poll
        poll_url = f"https://skyscanner89.p.rapidapi.com/flights/live/search/poll/{token}"
        for _ in range(10):
            time.sleep(2)
            poll_resp = requests.post(poll_url, headers=headers, timeout=30)
            poll_resp.raise_for_status()
            poll_data = poll_resp.json()
            if poll_data.get("status") == "RESULT_STATUS_COMPLETE":
                break
        else:
            raise Exception("Polling timeout")

        # Extract cheapest
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
            raise Exception("No flights found")
        return min(flights, key=lambda x: x["price"])

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status_code, message):
        self._send_json(status_code, {"error": message})
