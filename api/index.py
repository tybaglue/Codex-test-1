from app import create_app
from vercel_wsgi import handle

app = create_app()


def handler(event, context):
    return handle(app, event, context)
