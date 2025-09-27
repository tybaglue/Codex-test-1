from app import create_app

# Expose the raw Flask WSGI callable. Vercel's Python runtime will
# automatically treat any `app` attribute as the entrypoint for WSGI.
app = create_app()
