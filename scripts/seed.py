"""Seed the database with sample clients and orders."""
from datetime import date, timedelta
from decimal import Decimal
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import Client, Order, create_app, db, compute_next_public_id

SAMPLE_CLIENTS = [
    {
        "name": "Alice Chan",
        "email": "alice@example.com",
        "phone": "+8525550001",
        "address": "12 Flower Street, Central",
    },
    {
        "name": "Beacon Brands",
        "email": "orders@beaconbrands.hk",
        "phone": "+8525550002",
        "address": "88 Harbour Road, Wan Chai",
    },
    {
        "name": "Kenji Wong",
        "email": "kenji@example.com",
        "phone": "+8525550003",
        "address": "Flat 5B, Kowloon Tong",
    },
]


def ensure_client(data):
    client = Client.query.filter_by(email=data["email"]).first()
    if client:
        return client
    client = Client(**data)
    db.session.add(client)
    db.session.flush()
    return client


def create_order(client, days_from_now: int, items: str, price: str):
    order = Order(
        client=client,
        delivery_date=date.today() + timedelta(days=days_from_now),
        items_text=items,
        price_hkd=Decimal(price),
        status="unfulfilled",
        public_id=compute_next_public_id(),
    )
    db.session.add(order)


def main():
    app = create_app()
    with app.app_context():
        for data in SAMPLE_CLIENTS:
            ensure_client(data)
        db.session.commit()

        alice = Client.query.filter_by(email="alice@example.com").first()
        beacon = Client.query.filter_by(email="orders@beaconbrands.hk").first()
        kenji = Client.query.filter_by(email="kenji@example.com").first()

        create_order(alice, 0, "Seasonal bouquet with eucalyptus", "880")
        create_order(alice, 3, "Pastel arrangement for anniversary", "1200")
        create_order(beacon, 1, "Corporate table pieces x5", "3200")
        create_order(kenji, 7, "Birthday bouquet with sunflowers", "950")

        db.session.commit()
        print("Seed data inserted.")


if __name__ == "__main__":
    main()
