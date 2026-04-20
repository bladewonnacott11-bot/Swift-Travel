// ========== SEARCH FUNCTIONALITY (only runs on search.html) ==========
const searchForm = document.getElementById('search-form');
if (searchForm) {
  const searchResultsDiv = document.getElementById('search-results');
  
  // Set default departure date to tomorrow
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('departure').value = tomorrow.toISOString().split('T')[0];

  searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Loading state
    searchResultsDiv.style.display = 'block';
    searchResultsDiv.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; gap: 15px;">
        <div class="loader"></div>
        <p style="color: #94a3b8;">Searching for the best deals...</p>
      </div>
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
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (data.error) throw new Error(data.error);

      searchResultsDiv.innerHTML = `
        <div class="result-card">
          <div class="result-route">${data.origin} → ${data.destination}</div>
          <div class="result-price">${data.price.toFixed(0)} ${data.currency}</div>
          <div class="result-detail">${data.airline}</div>
          <div class="result-dates">${formatDate(data.depart_date)}</div>
          <a href="${data.deeplink || '#'}" target="_blank" class="result-btn">Book on Skyscanner →</a>
        </div>
      `;
    } catch (error) {
      console.error('Search error:', error);
      searchResultsDiv.innerHTML = `
        <div class="error-message">
          <i class="fas fa-exclamation-circle"></i>
          <p>${error.message || 'Search failed. Please try again.'}</p>
        </div>
      `;
    }
  });
}

// Date formatting helper (reused from home page)
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
