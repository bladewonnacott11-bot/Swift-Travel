/**
 * Swift Travels - Frontend Logic
 * Handles daily deals loading and live flight search.
 */

// ---------- Utility Functions ----------
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ---------- Daily Deals Loader ----------
async function loadDeals() {
  const flightCard = document.querySelector('#flight-card .card-content');
  const hotelCard = document.querySelector('#hotel-card .card-content');
  const carCard = document.querySelector('#car-card .card-content');
  const updateSpan = document.getElementById('update-time');

  try {
    const response = await fetch('data/deals.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const deals = await response.json();

    // Update timestamp
    if (deals.last_updated) {
      const d = new Date(deals.last_updated);
      updateSpan.textContent = `Last updated: ${d.toLocaleString()}`;
    }

    // Render Flight Deal
    if (deals.flights) {
      const f = deals.flights;
      flightCard.classList.remove('loading');
      flightCard.innerHTML = `
        <div class="deal-route">${f.origin} → ${f.destination}</div>
        <div class="deal-price">${f.price.toFixed(0)} ${f.currency}</div>
        <div class="deal-detail">${f.airline}</div>
        <div class="deal-dates">${formatDate(f.depart_date)}</div>
        <a href="${f.deeplink || '#'}" target="_blank" rel="noopener" class="book-btn">View Deal →</a>
      `;
    }

    // Render Hotel Deal (if exists)
    if (deals.hotels) {
      const h = deals.hotels;
      hotelCard.classList.remove('loading');
      hotelCard.innerHTML = `
        <div class="deal-route">${h.name}</div>
        <div class="deal-price">${h.price.toFixed(0)} ${h.currency}</div>
        <div class="deal-detail">${h.city}</div>
        <div class="deal-dates">${formatDate(h.checkin)} – ${formatDate(h.checkout)}</div>
        <a href="${h.deeplink || '#'}" target="_blank" rel="noopener" class="book-btn">View Deal →</a>
      `;
    }

    // Render Car Hire Deal (if exists)
    if (deals.cars) {
      const c = deals.cars;
      carCard.classList.remove('loading');
      carCard.innerHTML = `
        <div class="deal-route">${c.supplier}</div>
        <div class="deal-price">${c.price.toFixed(0)} ${c.currency}</div>
        <div class="deal-detail">${c.vehicle}</div>
        <div class="deal-dates">${formatDate(c.pickup_date)} – ${formatDate(c.dropoff_date)}</div>
        <a href="${c.deeplink || '#'}" target="_blank" rel="noopener" class="book-btn">View Deal →</a>
      `;
    }
  } catch (error) {
    console.error('Failed to load deals:', error);
    // Optionally show error state in cards
  }
}

// ---------- Live Search Form ----------
function initSearchForm() {
  const form = document.getElementById('search-form');
  if (!form) return;

  const resultsDiv = document.getElementById('search-results');
  const departInput = document.getElementById('departure');

  // Set default departure date to tomorrow
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  departInput.value = tomorrow.toISOString().split('T')[0];

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Show loading state
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;gap:15px;">
        <div class="loader"></div>
        <p style="color:#94a3b8;">Searching for the best deals...</p>
      </div>
    `;

    // Build payload
    const payload = {
      origin: document.getElementById('origin').value.trim().toUpperCase(),
      destination: document.getElementById('destination').value.trim().toUpperCase(),
      depart_date: departInput.value,
      adults: parseInt(document.getElementById('passengers').value, 10),
      currency: document.getElementById('currency').value,
      cabin: document.getElementById('cabin').value,
      locale: 'en-US',
      market: 'US'
    };

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}`);
      }

      // Render result
      resultsDiv.innerHTML = `
        <div class="result-card">
          <div class="result-route">${data.origin} → ${data.destination}</div>
          <div class="result-price">${data.price.toFixed(0)} ${data.currency}</div>
          <div class="result-detail">${data.airline}</div>
          <div class="result-dates">${formatDate(data.depart_date)}</div>
          <a href="${data.deeplink || '#'}" target="_blank" rel="noopener" class="result-btn">Book on Skyscanner →</a>
        </div>
      `;
    } catch (error) {
      console.error('Search error:', error);
      resultsDiv.innerHTML = `
        <div class="error-message">
          <i class="fas fa-exclamation-circle"></i>
          <p>${error.message || 'Search failed. Please try again.'}</p>
        </div>
      `;
    }
  });
}

// ---------- Initialize Everything ----------
document.addEventListener('DOMContentLoaded', () => {
  loadDeals();
  initSearchForm();
});
