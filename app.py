import os
import logging
import traceback
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24).hex())

# ------------------------------------------------------------
# Environment validation (with helpful warnings)
# ------------------------------------------------------------
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "skyscanner89.p.rapidapi.com")

if not RAPIDAPI_KEY:
    logger.warning("RAPIDAPI_KEY not set in environment. Skyscanner redirects will still work, but API features won't.")

# ------------------------------------------------------------
# Global Error Handler (premium style)
# ------------------------------------------------------------
@app.errorhandler(Exception)
def handle_exception(e):
    """Show detailed error in browser (safe for development)"""
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

# ------------------------------------------------------------
# Favicon route (prevents 404/500)
# ------------------------------------------------------------
@app.route('/favicon.ico')
def favicon():
    return '', 204

# ------------------------------------------------------------
# Homepage
# ------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# ------------------------------------------------------------
# Skyscanner Direct Redirect Routes
# ------------------------------------------------------------
@app.route('/search/flights', methods=['POST'])
def search_flights():
    """Redirect user directly to Skyscanner flight search"""
    try:
        origin = request.form.get('origin', '').strip()
        destination = request.form.get('destination', '').strip()
        departure_date = request.form.get('departureDate', '').strip()
        adults = request.form.get('adults', 1)

        # Basic validation
        if not origin or not destination or not departure_date:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('index'))

        # Build Skyscanner URL (using their standard pattern)
        # Example: https://www.skyscanner.net/transport/flights/united-kingdom/france/2025-06-01/
        # Replace spaces with hyphens for URL friendliness
        origin_slug = origin.replace(' ', '-').lower()
        dest_slug = destination.replace(' ', '-').lower()
        skyscanner_url = f"https://www.skyscanner.net/transport/flights/{origin_slug}/{dest_slug}/{departure_date}/?adults={adults}"
        
        logger.info(f"Redirecting flight search: {origin} → {destination} on {departure_date}")
        return redirect(skyscanner_url)
    
    except Exception as e:
        logger.error(f"Flight redirect error: {e}")
        flash('Invalid search parameters. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/search/hotels', methods=['POST'])
def search_hotels():
    """Redirect user directly to Skyscanner hotel search"""
    try:
        location = request.form.get('entityId', '').strip()
        check_in = request.form.get('checkIn', '').strip()
        check_out = request.form.get('checkOut', '').strip()
        guests = request.form.get('guests', 2)

        if not location or not check_in or not check_out:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('index'))

        # Build Skyscanner hotel URL
        location_slug = location.replace(' ', '-').lower()
        skyscanner_url = f"https://www.skyscanner.net/hotels/search/{location_slug}/{check_in}/{check_out}/{guests}"
        
        logger.info(f"Redirecting hotel search: {location} from {check_in} to {check_out}")
        return redirect(skyscanner_url)
    
    except Exception as e:
        logger.error(f"Hotel redirect error: {e}")
        flash('Invalid search parameters. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/search/cars', methods=['POST'])
def search_cars():
    """Redirect user directly to Skyscanner car hire search"""
    try:
        pickup = request.form.get('pickupLocation', '').strip()
        pickup_date = request.form.get('pickupDate', '').strip()
        dropoff_date = request.form.get('dropoffDate', '').strip()

        if not pickup or not pickup_date or not dropoff_date:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('index'))

        # Build Skyscanner car URL
        pickup_slug = pickup.replace(' ', '-').lower()
        skyscanner_url = f"https://www.skyscanner.net/carhire/search/{pickup_slug}/{pickup_date}/{dropoff_date}"
        
        logger.info(f"Redirecting car search: pick up at {pickup} on {pickup_date}")
        return redirect(skyscanner_url)
    
    except Exception as e:
        logger.error(f"Car redirect error: {e}")
        flash('Invalid search parameters. Please try again.', 'danger')
        return redirect(url_for('index'))

# ------------------------------------------------------------
# Legacy routes (optional – kept for backward compatibility)
# If you want to remove them, simply delete these three routes.
# They are not used by the new homepage but might be linked from elsewhere.
# ------------------------------------------------------------
@app.route('/flights')
def legacy_flights():
    """Legacy flight page – redirect to homepage (or could show form)"""
    return redirect(url_for('index'))

@app.route('/hotels')
def legacy_hotels():
    return redirect(url_for('index'))

@app.route('/cars')
def legacy_cars():
    return redirect(url_for('index'))

# ------------------------------------------------------------
# Health check endpoint (useful for uptime monitoring)
# ------------------------------------------------------------
@app.route('/health')
def health():
    return {"status": "ok", "message": "Swift Travels is running"}, 200

# ------------------------------------------------------------
# Run the app
# ------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
