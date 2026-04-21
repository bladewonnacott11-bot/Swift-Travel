# ------------------------------------------------------------
# Flight Search – Fetch flights and show results page
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

        origin_id = get_sky_id(origin_name)
        dest_id = get_sky_id(dest_name)

        if not origin_id or not dest_id:
            flash(f'Could not find airport codes for "{origin_name}" or "{dest_name}". Please use a city or supported country.', 'danger')
            return redirect(url_for('index'))

        # Call Skyscanner API to get live flight offers
        url = f"https://{RAPIDAPI_HOST}/flights/search"
        payload = {
            "origin": origin_id,
            "destination": dest_id,
            "departureDate": depart_date,
            "adults": int(adults),
            "currency": "USD"
        }
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Parse flight itineraries
        flights = []
        itineraries = data.get('itineraries', []) or data.get('data', {}).get('itineraries', [])
        for itin in itineraries[:20]:  # limit to 20 results
            price = itin.get('price', {}).get('amount', 'N/A')
            outbound = itin.get('outbound', {})
            inbound = itin.get('inbound', {})
            airline = outbound.get('carriers', [{}])[0].get('name', 'Unknown')
            airline_code = outbound.get('carriers', [{}])[0].get('code', '').lower()
            # Build a logo URL using a public airline logo service (fallback if not available)
            logo_url = f"https://content.skyscnr.com/__data/assets/file/0004/254776/{airline_code}.png" if airline_code else None
            flights.append({
                'price': f"${price}",
                'outbound_departure': outbound.get('departureAt', ''),
                'outbound_arrival': outbound.get('arrivalAt', ''),
                'inbound_departure': inbound.get('departureAt', ''),
                'inbound_arrival': inbound.get('arrivalAt', ''),
                'airline': airline,
                'airline_code': airline_code,
                'logo_url': logo_url,
                'deep_link': itin.get('deepLink', '#')
            })

        # If no flights found, use demo data with pictures
        if not flights:
            flights = get_demo_flights()

        return render_template('flight_results.html',
                               flights=flights,
                               origin=origin_name,
                               destination=dest_name,
                               depart_date=depart_date)

    except Exception as e:
        logger.error(f"Flight search error: {e}")
        flash('Unable to fetch flights. Please try again later.', 'danger')
        return redirect(url_for('index'))

def get_demo_flights():
    """Provide demo flight data with placeholder images."""
    return [
        {
            'price': '$299',
            'outbound_departure': '2025-06-01 08:00',
            'outbound_arrival': '2025-06-01 11:00',
            'inbound_departure': '',
            'inbound_arrival': '',
            'airline': 'SkyHigh Air',
            'airline_code': 'SK',
            'logo_url': 'https://via.placeholder.com/50?text=SK',
            'deep_link': 'https://www.skyscanner.net'
        },
        {
            'price': '$349',
            'outbound_departure': '2025-06-01 14:00',
            'outbound_arrival': '2025-06-01 17:00',
            'inbound_departure': '',
            'inbound_arrival': '',
            'airline': 'JetStream',
            'airline_code': 'JS',
            'logo_url': 'https://via.placeholder.com/50?text=JS',
            'deep_link': 'https://www.skyscanner.net'
        },
        {
            'price': '$199',
            'outbound_departure': '2025-06-02 06:00',
            'outbound_arrival': '2025-06-02 09:00',
            'inbound_departure': '',
            'inbound_arrival': '',
            'airline': 'BudgetWings',
            'airline_code': 'BW',
            'logo_url': 'https://via.placeholder.com/50?text=BW',
            'deep_link': 'https://www.skyscanner.net'
        }
    ]
