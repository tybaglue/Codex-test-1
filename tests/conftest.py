import pytest

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import Config, create_app, db


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    ADMIN_PASSWORD = "secret"
    SECRET_KEY = "testing"
    PUBLIC_FORM_TOKEN = None


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    ctx = app.app_context()
    ctx.push()

    yield app

    db.session.remove()
    db.drop_all()
    ctx.pop()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(client):
    with client.session_transaction() as session:
        session["is_admin"] = True
    return client
