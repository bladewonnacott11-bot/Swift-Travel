function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

async function loadDeals() {
  const flightCard = document.querySelector('#flight-card .card-content');
  const hotelCard = document.querySelector('#hotel-card .card-content');
  const carCard = document.querySelector('#car-card .card-content');
  const updateSpan = document.getElementById('update-time');

  try {
    const response = await fetch('data/deals.json');
    if (!response.ok) throw new Error('No deals data');
    const deals = await response.json();

    if (deals.last_updated) {
      updateSpan.textContent = `Last updated: ${new Date(deals.last_updated).toLocaleString()}`;
    }

    if (deals.flights) {
      const f = deals.flights;
      flightCard.classList.remove('loading');
      flightCard.innerHTML = `
        <div class="deal-route">${f.origin} → ${f.destination}</div>
        <div class="deal-price">${f.price.toFixed(0)} ${f.currency}</div>
        <div class="deal-detail">${f.airline}</div>
        <div class="deal-dates">${formatDate(f.depart_date)}</div>
        <a href="${f.deeplink || '#'}" target="_blank" class="book-btn">View Deal →</a>
      `;
    }

    if (deals.hotels) {
      const h = deals.hotels;
      hotelCard.classList.remove('loading');
      hotelCard.innerHTML = `
        <div class="deal-route">${h.name}</div>
        <div class="deal-price">${h.price.toFixed(0)} ${h.currency}</div>
        <div class="deal-detail">${h.city}</div>
        <div class="deal-dates">${formatDate(h.checkin)} – ${formatDate(h.checkout)}</div>
        <a href="${h.deeplink || '#'}" target="_blank" class="book-btn">View Deal →</a>
      `;
    }

    if (deals.cars) {
      const c = deals.cars;
      carCard.classList.remove('loading');
      carCard.innerHTML = `
        <div class="deal-route">${c.supplier}</div>
        <div class="deal-price">${c.price.toFixed(0)} ${c.currency}</div>
        <div class="deal-detail">${c.vehicle}</div>
        <div class="deal-dates">${formatDate(c.pickup_date)} – ${formatDate(c.dropoff_date)}</div>
        <a href="${c.deeplink || '#'}" target="_blank" class="book-btn">View Deal →</a>
      `;
    }
  } catch (e) {
    console.error(e);
  }
}

// Search form
const form = document.getElementById('search-form');
if (form) {
  const resultsDiv = document.getElementById('search-results');
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('departure').value = tomorrow.toISOString().split('T')[0];

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '<div class="loader"></div><p>Searching...</p>';

    const payload = {
      origin: document.getElementById('origin').value.toUpperCase(),
      destination: document.getElementById('destination').value.toUpperCase(),
      depart_date: document.getElementById('departure').value,
      adults: parseInt(document.getElementById('passengers').value),
      currency: document.getElementById('currency').value,
      cabin: document.getElementById('cabin').value,
      locale: 'en-US',
      market: 'US'
    };

    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      resultsDiv.innerHTML = `
        <div class="result-card">
          <div class="result-route">${data.origin} → ${data.destination}</div>
          <div class="result-price">${data.price.toFixed(0)} ${data.currency}</div>
          <div class="result-detail">${data.airline}</div>
          <div class="result-dates">${formatDate(data.depart_date)}</div>
          <a href="${data.deeplink || '#'}" target="_blank" class="result-btn">Book on Skyscanner →</a>
        </div>
      `;
    } catch (err) {
      resultsDiv.innerHTML = `<div class="error-message">${err.message}</div>`;
    }
  });
}

loadDeals();
