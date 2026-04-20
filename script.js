// ========== Daily Deals Loader (unchanged) ==========
async function loadDeals() {
  const flightCard = document.querySelector('#flight-card .card-body');
  const hotelCard = document.querySelector('#hotel-card .card-body');
  const carCard = document.querySelector('#car-card .card-body');
  const updateSpan = document.getElementById('update-time');

  try {
    const response = await fetch('data/deals.json');
    if (!response.ok) throw new Error('No deals data available');
    const deals = await response.json();

    if (deals.last_updated) {
      const d = new Date(deals.last_updated);
      updateSpan.textContent = `🕒 Last updated: ${d.toLocaleString()}`;
    }

    // Render Flight
    if (deals.flights) {
      const f = deals.flights;
      flightCard.classList.remove('loading');
      flightCard.innerHTML = `
        <div class="deal-route">${f.origin} ✈️ ${f.destination}</div>
        <div class="deal-price">${f.price.toFixed(2)} ${f.currency}</div>
        <div class="deal-detail">${f.airline}</div>
        <div class="deal-dates">📅 ${formatDate(f.depart_date)}</div>
        <a href="${f.deeplink || '#'}" target="_blank" class="book-btn">View on Skyscanner →</a>
      `;
    } else {
      flightCard.classList.remove('loading');
      flightCard.innerHTML = `<div class="error-message">😕 No flight deals found</div>`;
    }

    // Render Hotel
    if (deals.hotels) {
      const h = deals.hotels;
      hotelCard.classList.remove('loading');
      hotelCard.innerHTML = `
        <div class="deal-route">${h.name}</div>
        <div class="deal-price">${h.price.toFixed(2)} ${h.currency}</div>
        <div class="deal-detail">${h.city}</div>
        <div class="deal-dates">📅 ${formatDate(h.checkin)} – ${formatDate(h.checkout)}</div>
        <a href="${h.deeplink || '#'}" target="_blank" class="book-btn">View on Skyscanner →</a>
      `;
    } else {
      hotelCard.classList.remove('loading');
      hotelCard.innerHTML = `<div class="error-message">😕 No hotel deals found</div>`;
    }

    // Render Car Hire
    if (deals.cars) {
      const c = deals.cars;
      carCard.classList.remove('loading');
      carCard.innerHTML = `
        <div class="deal-route">${c.supplier}</div>
        <div class="deal-price">${c.price.toFixed(2)} ${c.currency}</div>
        <div class="deal-detail">${c.vehicle}</div>
        <div class="deal-dates">📍 ${c.pickup} → ${c.dropoff}<br>📅 ${formatDate(c.pickup_date)} – ${formatDate(c.dropoff_date)}</div>
        <a href="${c.deeplink || '#'}" target="_blank" class="book-btn">View on Skyscanner →</a>
      `;
    } else {
      carCard.classList.remove('loading');
      carCard.innerHTML = `<div class="error-message">😕 No car hire deals found</div>`;
    }

  } catch (error) {
    console.error('Failed to load deals:', error);
    [flightCard, hotelCard, carCard].forEach(card => {
      card.classList.remove('loading');
      card.innerHTML = `<div class="error-message">⚠️ Could not load deals.<br>Please check back later.</div>`;
    });
    updateSpan.textContent = '';
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ========== Search Functionality ==========
const searchForm = document.getElementById('search-form');
const searchResultsDiv = document.getElementById('search-results');

searchForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  // Show loading state
  searchResultsDiv.style.display = 'block';
  searchResultsDiv.innerHTML = `
    <div class="loader" style="margin: 20px auto;"></div>
    <p style="text-align: center; color: #94a3b8;">Searching for the cheapest flight...</p>
  `;

  const origin = document.getElementById('origin').value.toUpperCase();
  const destination = document.getElementById('destination').value.toUpperCase();
  const departDate = document.getElementById('departure').value;
  const adults = document.getElementById('passengers').value;
  const currency = document.getElementById('currency').value;
  const cabin = document.getElementById('cabin').value;

  const payload = {
    type: 'flight',
    origin,
    destination,
    depart_date: departDate,
    adults: parseInt(adults),
    currency,
    cabin,
    locale: 'en-US',
    market: 'US'
  };

  try {
    // Call Vercel serverless function
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    // Display result
    searchResultsDiv.innerHTML = `
      <div class="search-result-card">
        <div class="deal-route">${data.origin} ✈️ ${data.destination}</div>
        <div class="price">${data.price.toFixed(2)} ${data.currency}</div>
        <div class="deal-detail">${data.airline}</div>
        <div class="deal-dates">📅 ${formatDate(data.depart_date)}</div>
        <a href="${data.deeplink || '#'}" target="_blank" class="book-btn" style="margin-top: 15px;">View on Skyscanner →</a>
      </div>
    `;
  } catch (error) {
    console.error('Search error:', error);
    searchResultsDiv.innerHTML = `
      <div class="error-message" style="text-align: center;">
        ❌ ${error.message || 'Something went wrong. Please try again.'}
      </div>
    `;
  }
});

// Set default date to tomorrow
const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
document.getElementById('departure').value = tomorrow.toISOString().split('T')[0];

// Load daily deals on page load
loadDeals();
