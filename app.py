import os
import logging
import traceback
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24).hex())

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "skyscanner89.p.rapidapi.com"   # Adjust to your actual host

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST,
    "Content-Type": "application/json"
}

# ------------------------------------------------------------
# Country to airport IATA mapping (for common country names)
# ------------------------------------------------------------
COUNTRY_AIRPORT_MAP = {
    "united kingdom": "LON",      # London (any airport)
    "uk": "LON",
    "england": "LON",
    "united states": "NYC",       # New York (any airport)
    "usa": "NYC",
    "us": "NYC",
    "france": "PAR",
    "germany": "BER",             # Berlin
    "italy": "ROM",               # Rome
    "spain": "MAD",               # Madrid
    "portugal": "LIS",
    "netherlands": "AMS",
    "belgium": "BRU",
    "switzerland": "ZRH",
    "austria": "VIE",
    "sweden": "STO",
    "norway": "OSL",
    "denmark": "CPH",
    "finland": "HEL",
    "ireland": "DUB",
    "poland": "WAW",
    "greece": "ATH",
    "turkey": "IST",
    "uae": "DXB",
    "united arab emirates": "DXB",
    "india": "DEL",
    "china": "BJS",
    "japan": "TYO",
    "australia": "SYD",
    "canada": "YTO",
    "mexico": "MEX",
    "brazil": "SAO",
    "argentina": "BUE",
    "south africa": "JNB",
    "egypt": "CAI",
}

# ------------------------------------------------------------
# Global Error Handler
# ------------------------------------------------------------
@app.errorhandler(Exception)
def handle_exception(e):
    tb = traceback.format_exc()
    logger.error(f"Unhandled exception: {tb}")
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>⚠️ Server Error</title>
    <style>
        body {{ font-family: monospace; background: #f8d9da; padding: 2rem; }}
        .error {{ background: white; border-radius: 1rem; padding: 1.5rem; max-width: 1000px; margin: auto; }}
        pre {{ overflow-x: auto; background: #1e1e2f; color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; }}
    </style>
    </head>
    <body>
    <div class="error">
        <h2>🔥 Internal Server Error</h2>
        <pre>{tb}</pre>
        <p>Please check your configuration or try again later.</p>
        <a href="/">← Back to Home</a>
    </div>
    </body>
    </html>
    """, 500

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def index():
    return render_template('index.html')

# ------------------------------------------------------------
# Helper: Get Sky ID (IATA) for a location name (country or city)
# ------------------------------------------------------------
def get_sky_id(location_name, market="US", locale="en-US"):
    """Convert a country or city name into an IATA airport code."""
    location_lower = location_name.lower().strip()
    
    # 1. Check country mapping first
    for country, iata in COUNTRY_AIRPORT_MAP.items():
        if country in location_lower:
            logger.info(f"Mapped country '{location_name}' to IATA {iata}")
            return iata
    
    # 2. Try the API for city names
    url = f"https://{RAPIDAPI_HOST}/flights/searchAirport"
    params = {
        "market": market,
        "locale": locale,
        "query": location_name
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        places = data.get("data", []) or data.get("places", [])
        if places and len(places) > 0:
            sky_id = places[0].get("skyId") or places[0].get("iata")
            if sky_id:
                logger.info(f"API found IATA {sky_id} for '{location_name}'")
                return sky_id
        logger.warning(f"No airport found for '{location_name}' via API")
    except Exception as e:
        logger.error(f"Airport search error for {location_name}: {e}")
    
    # 3. Fallback: return None (will trigger error message)
    return None

# ------------------------------------------------------------
# Flight Search – Get deep link from Skyscanner
# ------------------------------------------------------------
@app.route('/search/flights', methods=['POST'])
def search_flights():
    try:
        origin_name = request.form.get('origin', '').strip()
        dest_name = request.form.get('destination', '').strip()
        depart_date = request.form.get('departureDate', '').strip()
        adults = request.form.get('adults', 1)
        max_price = request.form.get('maxPrice', '').strip()

        if not origin_name or not dest_name or not depart_date:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('index'))

        # Convert names to Sky IDs (IATA codes)
        origin_id = get_sky_id(origin_name)
        dest_id = get_sky_id(dest_name)

        if not origin_id or not dest_id:
            flash(f'Could not find airport codes for "{origin_name}" or "{dest_name}". Please use a specific city name (e.g., London, Paris) or a supported country name (e.g., United Kingdom, France).', 'danger')
            return redirect(url_for('index'))

        # Call the flight search endpoint that returns a deep link
        url = f"https://{RAPIDAPI_HOST}/flights/create-session"
        payload = {
            "origin": origin_id,
            "destination": dest_id,
            "departureDate": depart_date,
            "adults": int(adults),
            "cabinClass": "economy",
            "currency": "USD"
        }
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Extract the deep link (field name varies)
        deep_link = None
        if "deepLink" in data:
            deep_link = data["deepLink"]
        elif "sessionUrl" in data:
            deep_link = data["sessionUrl"]
        elif "redirectUrl" in data:
            deep_link = data["redirectUrl"]
        elif "itineraryUrl" in data:
            deep_link = data["itineraryUrl"]
        else:
            # Fallback: construct a manual URL (less reliable)
            deep_link = f"https://www.skyscanner.net/transport/flights/{origin_id}/{dest_id}/{depart_date}/"

        # Append max price if provided
        if max_price and max_price.isdigit():
            separator = '&' if '?' in deep_link else '?'
            deep_link += f"{separator}maxPrice={max_price}"

        logger.info(f"Redirecting to: {deep_link}")
        return redirect(deep_link)

    except Exception as e:
        logger.error(f"Flight redirect error: {e}")
        flash('Unable to generate a Skyscanner link. Please try again later.', 'danger')
        return redirect(url_for('index'))

# ------------------------------------------------------------
# Hotel Search – direct URL
# ------------------------------------------------------------
@app.route('/search/hotels', methods=['POST'])
def search_hotels():
    try:
        location = request.form.get('entityId', '').strip()
        check_in = request.form.get('checkIn', '').strip()
        check_out = request.form.get('checkOut', '').strip()
        guests = request.form.get('guests', 2)
        max_price = request.form.get('maxPrice', '').strip()

        if not location or not check_in or not check_out:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('index'))

        location_slug = quote(location.replace(' ', '-').lower())
        base_url = f"https://www.skyscanner.net/hotels/search/{location_slug}/{check_in}/{check_out}/"
        params = [f"guests={guests}"]
        if max_price and max_price.isdigit():
            params.append(f"maxPricePerNight={max_price}")
        skyscanner_url = base_url + "?" + "&".join(params)

        logger.info(f"Redirecting hotel: {skyscanner_url}")
        return redirect(skyscanner_url)

    except Exception as e:
        logger.error(f"Hotel redirect error: {e}")
        flash('Error generating hotel link.', 'danger')
        return redirect(url_for('index'))

# ------------------------------------------------------------
# Car Hire Search – direct URL
# ------------------------------------------------------------
@app.route('/search/cars', methods=['POST'])
def search_cars():
    try:
        pickup = request.form.get('pickupLocation', '').strip()
        pickup_date = request.form.get('pickupDate', '').strip()
        dropoff_date = request.form.get('dropoffDate', '').strip()
        max_price = request.form.get('maxPrice', '').strip()

        if not pickup or not pickup_date or not dropoff_date:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('index'))

        pickup_slug = quote(pickup.replace(' ', '-').lower())
        base_url = f"https://www.skyscanner.net/carhire/search/{pickup_slug}/{pickup_date}/{dropoff_date}/"
        if max_price and max_price.isdigit():
            base_url += f"?maxPricePerDay={max_price}"
        skyscanner_url = base_url

        logger.info(f"Redirecting car: {skyscanner_url}")
        return redirect(skyscanner_url)

    except Exception as e:
        logger.error(f"Car redirect error: {e}")
        flash('Error generating car hire link.', 'danger')
        return redirect(url_for('index'))

# ------------------------------------------------------------
# Legacy routes
# ------------------------------------------------------------
@app.route('/flights')
def legacy_flights():
    return redirect(url_for('index'))

@app.route('/hotels')
def legacy_hotels():
    return redirect(url_for('index'))

@app.route('/cars')
def legacy_cars():
    return redirect(url_for('index'))

@app.route('/health')
def health():
    return {"status": "ok", "message": "Swift Travels is running"}, 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
