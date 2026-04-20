# api/search.py
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
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        search_type = data.get('type', 'flight')
        
        if search_type == 'flight':
            result = self.search_flight(data)
        else:
            result = {"error": "Only flight search is currently supported"}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def search_flight(self, data):
        if not RAPIDAPI_KEY:
            return {"error": "API key not configured"}

        origin = data['origin']
        destination = data['destination']
        depart_date = data['depart_date']
        currency = data.get('currency', 'USD')
        locale = data.get('locale', 'en-US')
        market = data.get('market', 'US')
        adults = data.get('adults', 1)

        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "skyscanner89.p.rapidapi.com",
            "Content-Type": "application/json"
        }

        # Create search
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

        try:
            resp = requests.post(
                "https://skyscanner89.p.rapidapi.com/flights/live/search/create",
                headers=headers,
                json=payload,
                timeout=30
            )
            token = resp.json().get("sessionToken")
            if not token:
                return {"error": "No session token"}

            # Poll
            poll_url = f"https://skyscanner89.p.rapidapi.com/flights/live/search/poll/{token}"
            for _ in range(10):
                time.sleep(2)
                poll_resp = requests.post(poll_url, headers=headers, timeout=30)
                data = poll_resp.json()
                if data.get("status") == "RESULT_STATUS_COMPLETE":
                    break
            else:
                return {"error": "Polling timeout"}

            # Extract cheapest
            itineraries = data.get("content", {}).get("results", {}).get("itineraries", {})
            flights = []
            for bucket in itineraries.values():
                for item in bucket.get("items", []):
                    price = float(item.get("price", {}).get("amount", 999999))
                    currency = item.get("price", {}).get("unit", "USD")
                    airline = item.get("legs", [{}])[0].get("carriers", [{}])[0].get("name", "Unknown")
                    deeplink = item.get("deeplink", "")
                    flights.append({
                        "price": price,
                        "currency": currency,
                        "airline": airline,
                        "deeplink": deeplink,
                        "origin": origin,
                        "destination": destination,
                        "depart_date": depart_date
                    })
            
            if flights:
                return min(flights, key=lambda x: x["price"])
            else:
                return {"error": "No flights found"}
        except Exception as e:
            return {"error": str(e)}
