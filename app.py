import os
import requests
import traceback
from flask import Flask, render_template, request, flash, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24).hex())

# ------------------------------------------------------------
# Favicon route – prevents 500 error for /favicon.ico
# ------------------------------------------------------------
@app.route('/favicon.ico')
def favicon():
    return '', 204   # No content, no error

# ------------------------------------------------------------
# RapidAPI config
# ------------------------------------------------------------
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "skyscanner89.p.rapidapi.com")

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST,
    "Content-Type": "application/json"
}

USE_REAL_API = True   # Set to True to use live API

# ------------------------------------------------------------
# Dummy data (fallback)
# ------------------------------------------------------------
def get_dummy_flights(form_data):
    return [
        {'price': '$299', 'outbound_departure': '2025-06-01 08:00', 'outbound_arrival': '2025-06-01 11:00', 'inbound_departure': '', 'inbound_arrival': '', 'airline': 'SkyHigh Air'},
        {'price': '$349', 'outbound_departure': '2025-06-01 14:00', 'outbound_arrival': '2025-06-01 17:00', 'inbound_departure': '', 'inbound_arrival': '', 'airline': 'JetStream'},
        {'price': '$199', 'outbound_departure': '2025-06-02 06:00', 'outbound_arrival': '2025-06-02 09:00', 'inbound_departure': '', 'inbound_arrival': '', 'airline': 'BudgetWings'}
    ]

def get_dummy_hotels(form_data):
    return [
        {'name': 'Grand Plaza', 'price_per_night': '$150', 'rating': 4.8, 'address': '123 Main St'},
        {'name': 'Cozy Inn', 'price_per_night': '$89', 'rating': 4.2, 'address': '456 Oak Ave'},
        {'name': 'Luxury Suites', 'price_per_night': '$250', 'rating': 4.9, 'address': '789 Beach Rd'}
    ]

def get_dummy_cars(form_data):
    return [
        {'name': 'Toyota Corolla', 'price_per_day': '$45', 'supplier': 'Enterprise', 'transmission': 'Automatic'},
        {'name': 'Honda Civic', 'price_per_day': '$50', 'supplier': 'Hertz', 'transmission': 'Manual'},
        {'name': 'Tesla Model 3', 'price_per_day': '$120', 'supplier': 'Tesla Rentals', 'transmission': 'Automatic'}
    ]

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/flights', methods=['GET', 'POST'])
def flights():
    if request.method == 'POST':
        origin = request.form.get('origin', '').upper().strip()
        destination = request.form.get('destination', '').upper().strip()
        depart_date = request.form.get('depart_date')
        adults = request.form.get('adults', 1)
        
        if not all([origin, destination, depart_date]):
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('flights'))
        
        if not USE_REAL_API or not RAPIDAPI_KEY:
            flash('Using demo data (API not configured).', 'info')
            flights_data = get_dummy_flights(request.form)
            return render_template('flights.html', results=flights_data, form_data=request.form)
        
        # Try real API
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
            response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            flights_data = parse_flight_results(data)
            if not flights_data:
                flash('No flights found. Showing demo data.', 'warning')
                flights_data = get_dummy_flights(request.form)
            return render_template('flights.html', results=flights_data, form_data=request.form)
        except Exception as e:
            flash(f'API error: {str(e)}. Using demo data.', 'warning')
            flights_data = get_dummy_flights(request.form)
            return render_template('flights.html', results=flights_data, form_data=request.form)
    
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

@app.route('/hotels', methods=['GET', 'POST'])
def hotels():
    if request.method == 'POST':
        location = request.form.get('location', '').strip()
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        guests = request.form.get('guests', 2)
        
        if not all([location, check_in, check_out]):
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('hotels'))
        
        if not USE_REAL_API or not RAPIDAPI_KEY:
            flash('Using demo hotel data.', 'info')
            hotels_data = get_dummy_hotels(request.form)
            return render_template('hotels.html', results=hotels_data, form_data=request.form)
        
        url = f"https://{RAPIDAPI_HOST}/hotels/search"
        payload = {
            "location": location,
            "checkIn": check_in,
            "checkOut": check_out,
            "guests": int(guests),
            "currency": "USD"
        }
        try:
            response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            hotels_data = parse_hotel_results(data)
            if not hotels_data:
                flash('No hotels found. Showing demo data.', 'warning')
                hotels_data = get_dummy_hotels(request.form)
            return render_template('hotels.html', results=hotels_data, form_data=request.form)
        except Exception as e:
            flash(f'API error: {str(e)}. Using demo data.', 'warning')
            hotels_data = get_dummy_hotels(request.form)
            return render_template('hotels.html', results=hotels_data, form_data=request.form)
    
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
        
        if not USE_REAL_API or not RAPIDAPI_KEY:
            flash('Using demo car data.', 'info')
            cars_data = get_dummy_cars(request.form)
            return render_template('cars.html', results=cars_data, form_data=request.form)
        
        url = f"https://{RAPIDAPI_HOST}/cars/search"
        payload = {
            "pickUpLocation": pickup_location,
            "dropOffLocation": dropoff_location,
            "pickUpDate": pickup_date,
            "dropOffDate": dropoff_date,
            "currency": "USD"
        }
        try:
            response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            cars_data = parse_car_results(data)
            if not cars_data:
                flash('No cars found. Showing demo data.', 'warning')
                cars_data = get_dummy_cars(request.form)
            return render_template('cars.html', results=cars_data, form_data=request.form)
        except Exception as e:
            flash(f'API error: {str(e)}. Using demo data.', 'warning')
            cars_data = get_dummy_cars(request.form)
            return render_template('cars.html', results=cars_data, form_data=request.form)
    
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
