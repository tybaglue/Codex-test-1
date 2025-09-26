from datetime import date

from app import Client, Order, db


def create_order(client_name="Test Client", status="unfulfilled"):
    client = Client(name=client_name)
    db.session.add(client)
    db.session.flush()
    order = Order(
        client=client,
        delivery_date=date.today(),
        items_text="Roses and eucalyptus",
        price_hkd=1200,
        status=status,
        public_id=f"KGF-TEST-{client.id:04d}",
    )
    db.session.add(order)
    db.session.commit()
    return order


def test_toggle_order_status(admin_client):
    order = create_order()

    response = admin_client.post(f"/orders/{order.id}/toggle")
    assert response.status_code == 302

    updated = db.session.get(Order, order.id)
    assert updated.status == "fulfilled"


def test_calendar_feed_contains_order(client):
    order = create_order("Calendar Client")

    response = client.get("/calendar.ics")
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "BEGIN:VCALENDAR" in body
    assert f"SUMMARY:Delivery – {order.client.name}" in body
    assert order.public_id in body
