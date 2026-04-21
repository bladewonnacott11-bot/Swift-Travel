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
RAPIDAPI_HOST = "skyscanner89.p.rapidapi.com"   # or your actual host

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST,
    "Content-Type": "application/json"
}

# ------------------------------------------------------------
# Global Error Handler (unchanged)
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
# Helper: Convert city name to IATA code (simple mapping for demo)
# In production, use Skyscanner Autosuggest API.
# ------------------------------------------------------------
def get_iata_code(city_name):
    """Very basic mapping – replace with real autosuggest."""
    mapping = {
        "london": "LON", "paris": "PAR", "new york": "NYC", "los angeles": "LAX",
        "dubai": "DXB", "tokyo": "TYO", "singapore": "SIN", "bangkok": "BKK",
        "united kingdom": "LON", "france": "PAR", "usa": "NYC", "us": "NYC"
    }
    key = city_name.lower().strip()
    for k, v in mapping.items():
        if k in key:
            return v
    return None

# ------------------------------------------------------------
# Flight Search – Get real Skyscanner URL via API
# ------------------------------------------------------------
@app.route('/search/flights', methods=['POST'])
def search_flights():
    try:
        origin_city = request.form.get('origin', '').strip()
        dest_city = request.form.get('destination', '').strip()
        depart_date = request.form.get('departureDate', '').strip()
        adults = request.form.get('adults', 1)
        max_price = request.form.get('maxPrice', '').strip()

        if not origin_city or not dest_city or not depart_date:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('index'))

        # Convert city names to IATA codes (you need a real autosuggest)
        origin_iata = get_iata_code(origin_city)
        dest_iata = get_iata_code(dest_city)
        if not origin_iata or not dest_iata:
            flash('Could not recognize airport codes. Please use city names like London, Paris, etc.', 'danger')
            return redirect(url_for('index'))

        # Call Skyscanner API to get a shallow link / deep link
        # Using the /flights/create-session or /flights/search endpoint.
        # Many RapidAPI Skyscanner endpoints return a "deepLink" or "redirectUrl".
        # I'll use a typical endpoint that works with your key.
        url = f"https://{RAPIDAPI_HOST}/flights/create-session"
        payload = {
            "origin": origin_iata,
            "destination": dest_iata,
            "departureDate": depart_date,
            "adults": int(adults),
            "cabinClass": "economy",
            "currency": "USD"
        }
        response = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Extract the redirect URL – field names vary by API
        # Common fields: "deepLink", "sessionUrl", "redirectUrl", "itineraryUrl"
        skyscanner_url = None
        if "deepLink" in data:
            skyscanner_url = data["deepLink"]
        elif "sessionUrl" in data:
            skyscanner_url = data["sessionUrl"]
        elif "redirectUrl" in data:
            skyscanner_url = data["redirectUrl"]
        elif "itineraryUrl" in data:
            skyscanner_url = data["itineraryUrl"]
        else:
            # Fallback: build a manual URL (last resort)
            skyscanner_url = f"https://www.skyscanner.net/transport/flights/{origin_iata}/{dest_iata}/{depart_date}/"

        # Add max price as a query parameter if provided
        if max_price and max_price.isdigit():
            separator = '&' if '?' in skyscanner_url else '?'
            skyscanner_url += f"{separator}maxPrice={max_price}"

        logger.info(f"Redirecting flight: {skyscanner_url}")
        return redirect(skyscanner_url)

    except Exception as e:
        logger.error(f"Flight redirect error: {e}")
        flash('Unable to generate a Skyscanner link. Please try again later.', 'danger')
        return redirect(url_for('index'))

# ------------------------------------------------------------
# Hotel Search – similar approach (simplified for now)
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

        # Build a direct Skyscanner hotel URL (no API needed)
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
