# KGF Orders MVP

Minimal florist order manager for Kew Garden Flowers. Built as a mobile-first Flask app that unifies website, WhatsApp, Instagram, and brand orders.

## Features
- Dashboard with unfulfilled count and delivery snapshots (today, week, month)
- Orders table with HTMX filters and inline status toggles
- Order detail view with quick actions (toggle, edit, delete)
- Public/admin order form with honeypot and rate limiting
- Client directory with search, detail pages, and linked orders
- Calendar view plus `/calendar.ics` feed for Google Calendar subscriptions
- CSV exports for orders and clients
- Seed script and CLI helper to generate the next `public_id`
- Minimal pytest coverage for status toggle and ICS feed

## Tech Stack
- Python 3 + Flask + Flask-SQLAlchemy
- SQLite (file-backed by default)
- HTMX for partial updates
- Tailwind CSS via CDN

## Getting Started

### 1. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables
Copy `.env.example` to `.env` (or define the variables directly in Replit):

- `ADMIN_PASSWORD` (required) – password for `/login`
- `PUBLIC_FORM_TOKEN` (optional) – query token required for public order form access
- `CALENDAR_TOKEN` (optional) – query token required for `/calendar.ics`
- `APP_TIMEZONE` (default `Europe/London`)
- `RATE_LIMIT_WINDOW` / `RATE_LIMIT_REQUESTS` – throttle for public order form submissions

### 3. Initialize the database
```bash
python main.py  # first run will create kgf_orders.db
python scripts/seed.py  # optional sample data
```

### 4. Run the app locally
```bash
FLASK_APP=main.py flask run
# or
python main.py
```

### Deploying on Replit
1. Create a new Replit (Python template) and upload this project or connect the GitHub repo.
2. Add `requirements.txt` packages via the Replit package manager (auto-detected) or `pip install -r requirements.txt`.
3. Set environment variables in the Replit Secrets panel:
   - `ADMIN_PASSWORD`
   - Optionally `PUBLIC_FORM_TOKEN`, `CALENDAR_TOKEN`, `APP_TIMEZONE`
4. Use `python main.py` as the Run command. Replit will show the web preview URL.

### Running tests
```bash
pytest
```

## Using the App
- **Login:** visit `/login` and sign in with `ADMIN_PASSWORD`.
- **Dashboard:** shows key counts, recent orders, and quick links.
- **Orders:** filter via the status dropdown or search box (HTMX updates the table only). Toggle status inline or open an order to edit.
- **Public order form:** share `/orders/new?token=YOUR_TOKEN` if `PUBLIC_FORM_TOKEN` is set. Includes honeypot field and rate limiting for spam protection.
- **Clients:** manage contact details and review their order history.
- **Calendar:** `/calendar` lists deliveries by day; subscribe to `/calendar.ics` in Google Calendar. If `CALENDAR_TOKEN` is set, append `?token=...` to the URL when subscribing.
- **Exports:** download `/export.csv` and `/clients.csv` for bookkeeping.

## Utilities
- `scripts/seed.py` – add sample clients/orders (skips if data already exists).
- `scripts/next_public_id.py` – prints the next order `public_id` (uses current year).

## Directory Overview
```
app/
  __init__.py        # Flask app factory
  models.py          # SQLAlchemy models
  routes/            # Blueprints (auth, dashboard, orders, clients, calendar, exports)
  templates/         # Jinja templates (Tailwind + HTMX)
  utils.py           # Helpers (auth guard, currency filter, rate limiter)
main.py              # Entry point
requirements.txt     # Python dependencies
scripts/             # Seed and CLI utilities
tests/               # Pytest suite
```

## ICS subscription tips
- Google Calendar: **Settings > Add calendar > From URL** and paste the `/calendar.ics` link (include `?token=` if required).
- Calendar refreshes are controlled by Google; allow up to a few hours for updates.

## Data exports
- `/export.csv` includes `order_id, public_id, client_name, delivery_date, status, price_hkd, items_text, notes` with HKD values including cents.
- `/clients.csv` includes `client_id, name, phone, email, address, notes, created_at`.

## Deploying to Vercel
1. Pull the latest code so the latest `api/index.py` is deployed.
2. Create a `.env` file alongside `main.py` with at least:
   - `ADMIN_PASSWORD`
   - `SECRET_KEY`
   - (optional) `PUBLIC_FORM_TOKEN`
3. In the Vercel dashboard, import this repository as a new project.
4. Under **Settings → Environment Variables**, add the same variables (copy from your `.env`).
5. Deploy. `vercel.json` routes every request to `api/index.py`, which exports the Flask app as a WSGI callable that Vercel invokes directly.
6. For later updates, push to the default branch or trigger a redeploy in Vercel.

> **Note:** Vercel serverless functions have a read-only filesystem. The app automatically falls back to storing the SQLite database in `/tmp/kgf.db` when the `VERCEL` environment variable is present. `/tmp` is ephemeral, so data will not persist between deployments or cold starts—connect an external database for production use.
