# KGF Orders MVP

Minimal florist order manager for Kew Garden Flowers. Built with Flask, SQLite and HTMX for quick deployment on Replit.

## Features

- Password-protected admin dashboard with order metrics and quick links.
- Orders list with search, status filters, inline fulfilment toggle (HTMX) and detail views.
- Mobile-friendly order form that supports public submissions when gated by a token.
- Client directory with contact management and linked order history.
- Delivery calendar view plus an ICS feed for subscribing in Google Calendar.
- CSV exports for orders and clients.
- Seed script and CLI helper to generate the next public order ID.

## Getting started on Replit

1. Create a new Replit project using the **Python** template.
2. Upload the repository files into the Replit workspace.
3. In the Replit shell, install dependencies: `pip install -r requirements.txt`.
4. Create a `.env` file in Replit with the environment variables shown below (at minimum set `ADMIN_PASSWORD`).
5. Click **Run** to start the Flask server (`main.py`). Replit will expose the web preview URL automatically.

### Environment variables

| Variable | Description |
| --- | --- |
| `ADMIN_PASSWORD` | Password required to access the admin dashboard. |
| `PUBLIC_FORM_TOKEN` | Optional token required for the public `/orders/new` form. Leave unset for admin-only usage. |
| `SECRET_KEY` | Flask session secret. Replit generates one automatically but you can override it. |
| `RATELIMIT_MAX_PER_HOUR` | Optional rate limit for the public order form (default `10`). |

You can set these in Replit under **Secrets** or in a `.env` file when running locally.

### Database

The app uses SQLite by default (`kgf.db`). The database file will be created on first run.

To populate sample data for demos or testing, run:

```bash
python scripts/seed.py
```

To print the next public order ID without creating an order:

```bash
python scripts/next_public_id.py
```

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD="your-password"
flask --app main run --debug
```

The app listens on `http://localhost:5000`.

## Tests

Run the automated tests with:

```bash
pytest
```

This covers the order status toggle endpoint and the ICS calendar feed.

## Calendar subscription

- Visit `/calendar.ics` on your deployed instance to download the iCalendar feed.
- In Google Calendar, choose **Other calendars → Add by URL** and paste the `/calendar.ics` link.
- Deliveries will appear as all-day events titled `Delivery – <Client Name>`.

## Data export

- `/export.csv` downloads all active orders in CSV format.
- `/clients.csv` downloads all active clients.

Both endpoints require admin authentication.
