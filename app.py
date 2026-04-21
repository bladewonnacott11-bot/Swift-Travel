import os
import logging
import traceback
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24).hex())

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "skyscanner89.p.rapidapi.com")

if not RAPIDAPI_KEY:
    logger.warning("RAPIDAPI_KEY not set in environment.")

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
# Skyscanner Redirect Routes (with maxPrice support)
# ------------------------------------------------------------
@app.route('/search/flights', methods=['POST'])
def search_flights():
    try:
        origin = request.form.get('origin', '').strip()
        destination = request.form.get('destination', '').strip()
        departure_date = request.form.get('departureDate', '').strip()
        adults = request.form.get('adults', 1)
        max_price = request.form.get('maxPrice', '').strip()

        if not origin or not destination or not departure_date:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('index'))

        # URL‑encode the slugs
        origin_slug = quote(origin.replace(' ', '-').lower())
        dest_slug = quote(destination.replace(' ', '-').lower())

        # Base URL (without trailing slash to avoid double slashes)
        base_url = f"https://www.skyscanner.net/transport/flights/{origin_slug}/{dest_slug}/{departure_date}"

        # Build query parameters
        params = [f"adults={adults}"]
        if max_price and max_price.isdigit():
            params.append(f"maxPrice={max_price}")

        skyscanner_url = base_url + "?" + "&".join(params)
        logger.info(f"Flight redirect: {skyscanner_url}")
        return redirect(skyscanner_url)

    except Exception as e:
        logger.error(f"Flight redirect error: {e}")
        flash('Invalid search parameters. Please try again.', 'danger')
        return redirect(url_for('index'))

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
        base_url = f"https://www.skyscanner.net/hotels/search/{location_slug}/{check_in}/{check_out}"

        params = [f"guests={guests}"]
        if max_price and max_price.isdigit():
            params.append(f"maxPricePerNight={max_price}")

        skyscanner_url = base_url + "?" + "&".join(params)
        logger.info(f"Hotel redirect: {skyscanner_url}")
        return redirect(skyscanner_url)

    except Exception as e:
        logger.error(f"Hotel redirect error: {e}")
        flash('Invalid search parameters. Please try again.', 'danger')
        return redirect(url_for('index'))

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
        base_url = f"https://www.skyscanner.net/carhire/search/{pickup_slug}/{pickup_date}/{dropoff_date}"

        params = []
        if max_price and max_price.isdigit():
            params.append(f"maxPricePerDay={max_price}")

        skyscanner_url = base_url + ("?" + "&".join(params) if params else "")
        logger.info(f"Car redirect: {skyscanner_url}")
        return redirect(skyscanner_url)

    except Exception as e:
        logger.error(f"Car redirect error: {e}")
        flash('Invalid search parameters. Please try again.', 'danger')
        return redirect(url_for('index'))

# ------------------------------------------------------------
# Legacy routes (redirect to home)
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
