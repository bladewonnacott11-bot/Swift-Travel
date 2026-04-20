# Swift Travels ✈️

A premium travel deals website that displays daily updated cheap flights, hotels, and car rentals from Skyscanner, plus a live search feature.

## Features
- **Live Flight Search** – Enter origin, destination, dates and get the cheapest flight instantly.
- **Daily Auto-Updated Deals** – GitHub Action runs every day at 08:00 UTC to refresh deals.
- **Premium Glassmorphism Design** – Fully responsive, modern UI.
- **Free Hosting** – Deployed on Vercel (frontend + API) with GitHub Actions.

## Tech Stack
- **Frontend:** HTML, CSS, JavaScript (Vanilla)
- **Backend API:** Python (Vercel Serverless Function)
- **Data:** Skyscanner RapidAPI
- **Automation:** GitHub Actions

## Setup
1. Clone this repository.
2. Add your `RAPIDAPI_KEY` to Vercel Environment Variables.
3. Add the same key and search parameters as GitHub Secrets.
4. Deploy to Vercel (Framework Preset: **Other**).

## File Structure
- `api/search.py` – Vercel serverless function for live search.
- `travel_fetcher.py` – Script run by GitHub Actions to update `data/deals.json`.
- `index.html`, `style.css`, `script.js` – Frontend assets.

## License
MIT
