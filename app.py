import os
import requests
import traceback  # 👈 ADDED for error details
from flask import Flask, render_template, request, flash, redirect, url_for, render_template_string  # 👈 ADDED render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ------------------------------------------------------------
# ERROR HANDLER – shows detailed error in browser (REMOVE in production)
# ------------------------------------------------------------
@app.errorhandler(500)
def internal_server_error(e):
    tb = traceback.format_exc()
    return render_template_string(f"""
    <div style="background:#f8d7da; color:#721c24; padding:20px; margin:20px; border-radius:8px; font-family:monospace;">
        <h2>🔥 Internal Server Error (500)</h2>
        <pre style="background:#fff; padding:15px; overflow:auto;">{tb}</pre>
        <p>Check your API keys, endpoints, or template syntax.</p>
    </div>
    """), 500

# ------------------------------------------------------------
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST,
    "Content-Type": "application/json"
}

# -------------------------------------------------------------------
# Homepage
# -------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# -------------------------------------------------------------------
# Flight Search
# -------------------------------------------------------------------
@app.route('/flights', methods=['GET', 'POST'])
def flights():
    if request.method == 'POST':
        origin = request.form.get('origin', '').upper().strip()
        destination = request.form.get('destination', '').upper().strip()
        depart_date = request.form.get('depart_date')
        adults = request.form.get('adults', 1)
        
        if not all([origin, destination, depart_date]):
            flash('Please fill all required fields (origin, destination, departure date).', 'danger')
            return redirect(url_for('flights'))
        
        url = f"https://{RAPIDAPI_HOST}/flights/search"
        
        payload = {
            "origin": origin,
            "destination": destination,
            "departureDate": depart_date,
            "adults": int(adults),
            "cabinClass": "economy",
            "currency": "USD"
        }
        
        try:
            response = requests.post(url, json=payload, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            flights_data = parse_flight_results(data)
            return render_template('flights.html', results=flights_data, form_data=request.form)
        
        except requests.exceptions.RequestException as e:
            flash(f'API error: {str(e)}', 'danger')
            return redirect(url_for('flights'))
        except Exception as e:
            flash(f'Unexpected error: {str(e)}', 'danger')
            return redirect(url_for('flights'))
    
    return render_template('flights.html', results=None, form_data={})

def parse_flight_results(data):
    flights = []
    try:
        itineraries = data.get('itineraries', []) or data.get('data', {}).get('itineraries', [])
        for itin in itineraries[:20]:
            price = itin.get('price', {}).get('raw', 'N/A')
            outbound = itin.get('outbound', {})
            inbound = itin.get('inbound', {})
            flights.append({
                'price': f"${price}" if price != 'N/A' else 'Price on request',
                'outbound_departure': outbound.get('departureAt', ''),
                'outbound_arrival': outbound.get('arrivalAt', ''),
                'inbound_departure': inbound.get('departureAt', ''),
                'inbound_arrival': inbound.get('arrivalAt', ''),
                'airline': outbound.get('carriers', [{}])[0].get('name', 'Unknown')
            })
    except Exception:
        pass
    return flights

# -------------------------------------------------------------------
# Hotel Search
# -------------------------------------------------------------------
@app.route('/hotels', methods=['GET', 'POST'])
def hotels():
    if request.method == 'POST':
        location = request.form.get('location', '').strip()
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        guests = request.form.get('guests', 2)
        
        if not all([location, check_in, check_out]):
            flash('Please fill all required fields (location, check-in, check-out).', 'danger')
            return redirect(url_for('hotels'))
        
        url = f"https://{RAPIDAPI_HOST}/hotels/search"
        
        payload = {
            "location": location,
            "checkIn": check_in,
            "checkOut": check_out,
            "guests": int(guests),
            "currency": "USD"
        }
        
        try:
            response = requests.post(url, json=payload, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            hotels_data = parse_hotel_results(data)
            return render_template('hotels.html', results=hotels_data, form_data=request.form)
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('hotels'))
    
    return render_template('hotels.html', results=None, form_data={})

def parse_hotel_results(data):
    hotels = []
    try:
        hotels_list = data.get('hotels', []) or data.get('data', {}).get('hotels', [])
        for hotel in hotels_list[:20]:
            hotels.append({
                'name': hotel.get('name', 'Unknown'),
                'price_per_night': f"${hotel.get('pricePerNight', {}).get('amount', 'N/A')}",
                'rating': hotel.get('rating', 'N/A'),
                'address': hotel.get('address', {}).get('street', '')
            })
    except Exception:
        pass
    return hotels

# -------------------------------------------------------------------
# Car Hire Search
# -------------------------------------------------------------------
@app.route('/cars', methods=['GET', 'POST'])
def cars():
    if request.method == 'POST':
        pickup_location = request.form.get('pickup_location', '').upper().strip()
        dropoff_location = request.form.get('dropoff_location', '').upper().strip()
        pickup_date = request.form.get('pickup_date')
        dropoff_date = request.form.get('dropoff_date')
        
        if not all([pickup_location, dropoff_location, pickup_date, dropoff_date]):
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('cars'))
        
        url = f"https://{RAPIDAPI_HOST}/cars/search"
        
        payload = {
            "pickUpLocation": pickup_location,
            "dropOffLocation": dropoff_location,
            "pickUpDate": pickup_date,
            "dropOffDate": dropoff_date,
            "currency": "USD"
        }
        
        try:
            response = requests.post(url, json=payload, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            cars_data = parse_car_results(data)
            return render_template('cars.html', results=cars_data, form_data=request.form)
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('cars'))
    
    return render_template('cars.html', results=None, form_data={})

def parse_car_results(data):
    cars = []
    try:
        cars_list = data.get('vehicles', []) or data.get('data', {}).get('vehicles', [])
        for car in cars_list[:20]:
            cars.append({
                'name': car.get('name', 'Unknown'),
                'price_per_day': f"${car.get('pricePerDay', {}).get('amount', 'N/A')}",
                'supplier': car.get('supplier', {}).get('name', 'Unknown'),
                'transmission': car.get('transmission', 'N/A')
            })
    except Exception:
        pass
    return cars

# -------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
