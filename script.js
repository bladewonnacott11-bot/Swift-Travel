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
    if (!response.ok) throw new Error('No deals data available');
    const deals = await response.json();

    if (deals.last_updated) {
      const d = new Date(deals.last_updated);
      updateSpan.textContent = `Last updated: ${d.toLocaleString()}`;
    } else {
      updateSpan.textContent = 'Last updated: recently';
    }

    // Flight
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
    } else {
      flightCard.classList.remove('loading');
      flightCard.innerHTML = `<p style="color: #f87171;">No flight deals found</p>`;
    }

    // Hotel
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
    } else {
      hotelCard.classList.remove('loading');
      hotelCard.innerHTML = `<p style="color: #f87171;">No hotel deals found</p>`;
    }

    // Car
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
    } else {
      carCard.classList.remove('loading');
      carCard.innerHTML = `<p style="color: #f87171;">No car deals found</p>`;
    }
  } catch (error) {
    console.error('Failed to load deals:', error);
    [flightCard, hotelCard, carCard].forEach(card => {
      card.classList.remove('loading');
      card.innerHTML = `<p style="color: #f87171;">Could not load deals</p>`;
    });
    updateSpan.textContent = 'Last updated: unavailable';
  }
}

loadDeals();
