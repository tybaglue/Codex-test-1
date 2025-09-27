import os
import calendar
from datetime import datetime, date, timedelta
from functools import wraps
from decimal import Decimal, InvalidOperation
from typing import Optional

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Response,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_


db = SQLAlchemy()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    _default_db = "sqlite:///kgf.db"
    if os.environ.get("VERCEL"):
        _default_db = "sqlite:////tmp/kgf.db"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", _default_db)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
    PUBLIC_FORM_TOKEN = os.environ.get("PUBLIC_FORM_TOKEN")
    RATELIMIT_MAX_PER_HOUR = int(os.environ.get("RATELIMIT_MAX_PER_HOUR", 10))


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_archived = db.Column(db.Boolean, default=False)

    orders = db.relationship("Order", backref="client", lazy=True)

    def active_orders(self):
        return [order for order in self.orders if not order.is_archived]


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(40), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="unfulfilled", nullable=False)
    items_text = db.Column(db.Text)
    price_hkd = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = db.Column(db.Boolean, default=False)

    def toggle_status(self):
        self.status = "fulfilled" if self.status == "unfulfilled" else "unfulfilled"


RATELIMIT_CACHE = {}


def compute_next_public_id() -> str:
    today = datetime.utcnow().strftime("%Y")
    last_order = (
        Order.query.filter(Order.public_id.like(f"KGF-{today}-%"))
        .order_by(Order.id.desc())
        .first()
    )
    if last_order and last_order.public_id:
        try:
            seq = int(last_order.public_id.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"KGF-{today}-{seq:04d}"


def create_app(config_object: Optional[Config] = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)

    return app


def register_routes(app: Flask) -> None:
    @app.before_request
    def load_globals():
        g.admin_authenticated = session.get("is_admin", False)
        g.public_form_token = app.config.get("PUBLIC_FORM_TOKEN")

    def require_admin(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("is_admin"):
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)

        return wrapped

    def verify_public_token():
        token = app.config.get("PUBLIC_FORM_TOKEN")
        if not token:
            return True
        return request.args.get("token") == token

    def enforce_ratelimit():
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        now = datetime.utcnow()
        cache = RATELIMIT_CACHE.get(ip)
        max_per_hour = app.config.get("RATELIMIT_MAX_PER_HOUR", 10)
        if cache:
            window_start, count = cache
            if (now - window_start).total_seconds() < 3600:
                if count >= max_per_hour:
                    return False
                RATELIMIT_CACHE[ip] = (window_start, count + 1)
                return True
        RATELIMIT_CACHE[ip] = (now, 1)
        return True

    def parse_date(value: str) -> Optional[date]:
        if not value:
            return None
        return datetime.strptime(value, "%Y-%m-%d").date()

    def render_order_row(order: Order):
        return render_template("orders/_order_row.html", order=order)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            password = request.form.get("password", "")
            if password == app.config.get("ADMIN_PASSWORD") and password:
                session["is_admin"] = True
                flash("Logged in successfully.", "success")
                next_url = request.args.get("next") or url_for("dashboard")
                return redirect(next_url)
            error = "Invalid password"
        return render_template("auth/login.html", error=error)

    @app.route("/logout")
    def logout():
        session.pop("is_admin", None)
        flash("Logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/")
    @require_admin
    def dashboard():
        today = datetime.utcnow().date()
        week_end = today + timedelta(days=6)
        month_end = date(
            today.year,
            today.month,
            calendar.monthrange(today.year, today.month)[1],
        )

        unfulfilled_count = Order.query.filter_by(status="unfulfilled", is_archived=False).count()
        todays_deliveries = Order.query.filter(
            Order.delivery_date == today, Order.is_archived.is_(False)
        ).count()
        week_deliveries = Order.query.filter(
            Order.delivery_date.between(today, week_end), Order.is_archived.is_(False)
        ).count()
        month_deliveries = Order.query.filter(
            Order.delivery_date.between(today.replace(day=1), month_end),
            Order.is_archived.is_(False),
        ).count()

        recent_orders = (
            Order.query.filter(Order.is_archived.is_(False))
            .order_by(Order.created_at.desc())
            .limit(10)
            .all()
        )

        return render_template(
            "dashboard.html",
            stats={
                "unfulfilled": unfulfilled_count,
                "today": todays_deliveries,
                "week": week_deliveries,
                "month": month_deliveries,
            },
            recent_orders=recent_orders,
        )

    @app.route("/orders")
    @require_admin
    def orders_list():
        status_filter = request.args.get("status", "unfulfilled")
        query = request.args.get("q", "").strip()
        orders_query = Order.query.join(Client).filter(Order.is_archived.is_(False))

        if status_filter in {"fulfilled", "unfulfilled"}:
            orders_query = orders_query.filter(Order.status == status_filter)
        
        if query:
            like = f"%{query}%"
            orders_query = orders_query.filter(
                or_(
                    Client.name.ilike(like),
                    Client.email.ilike(like),
                    Client.phone.ilike(like),
                    Order.public_id.ilike(like),
                )
            )

        orders = orders_query.order_by(Order.delivery_date.asc()).all()

        if request.headers.get("HX-Request"):
            return render_template("orders/_order_rows.html", orders=orders)

        return render_template("orders/list.html", orders=orders, status_filter=status_filter, q=query)

    @app.route("/orders/<int:order_id>")
    @require_admin
    def order_detail(order_id: int):
        order = Order.query.filter_by(id=order_id, is_archived=False).first_or_404()
        return render_template("orders/detail.html", order=order)

    @app.route("/orders/<int:order_id>/toggle", methods=["POST"])
    @require_admin
    def toggle_order(order_id: int):
        order = Order.query.filter_by(id=order_id, is_archived=False).first_or_404()
        order.toggle_status()
        db.session.commit()
        if request.headers.get("HX-Request"):
            return render_order_row(order)
        flash("Order status updated.", "success")
        return redirect(url_for("orders_list"))

    @app.route("/orders/<int:order_id>/delete", methods=["POST"])
    @require_admin
    def delete_order(order_id: int):
        order = Order.query.filter_by(id=order_id, is_archived=False).first_or_404()
        order.is_archived = True
        db.session.commit()
        flash("Order archived.", "info")
        return redirect(url_for("orders_list"))

    def get_or_create_client(data):
        email = data.get("email", "").strip().lower()
        phone = data.get("phone", "").strip()
        client = None
        if email:
            client = Client.query.filter(func.lower(Client.email) == email).first()
        if not client and phone:
            client = Client.query.filter(Client.phone == phone).first()
        if client:
            client.name = data.get("name", client.name)
            client.address = data.get("address", client.address)
        else:
            client = Client(
                name=data.get("name", "Unknown"),
                phone=phone,
                email=email,
                address=data.get("address"),
            )
            db.session.add(client)
            db.session.flush()
        return client

    def require_public_access():
        if g.admin_authenticated:
            return True
        if not verify_public_token():
            abort(403)
        return True

    @app.route("/orders/new", methods=["GET", "POST"])
    def new_order():
        require_public_access()

        form_data = request.form if request.method == "POST" else None
        form_token = request.args.get("token")

        if request.method == "POST":
            honeypot = request.form.get("website")
            if honeypot:
                abort(400)
            if not enforce_ratelimit():
                flash("Too many submissions, please try again later.", "error")
                return render_template("orders/new.html", form_data=form_data, form_token=form_token)

            form = request.form
            client_data = {
                "name": form.get("client_name", "").strip(),
                "phone": form.get("client_phone", "").strip(),
                "email": form.get("client_email", "").strip(),
                "address": form.get("client_address", "").strip(),
            }
            delivery_date = parse_date(form.get("delivery_date"))
            items_text = form.get("items_text", "")
            notes = form.get("notes", "")
            price_raw = form.get("price_hkd")
            price = None
            if price_raw:
                try:
                    price = Decimal(price_raw)
                except InvalidOperation:
                    flash("Please enter a valid price.", "error")
                    return render_template("orders/new.html", form_data=form_data, form_token=form_token)

            if not client_data["name"] or not delivery_date:
                flash("Please provide client name and delivery date.", "error")
                return render_template("orders/new.html", form_data=form_data, form_token=form_token)

            client = get_or_create_client(client_data)
            order = Order(
                client=client,
                delivery_date=delivery_date,
                items_text=items_text,
                notes=notes,
                price_hkd=price,
                public_id=compute_next_public_id(),
            )
            db.session.add(order)
            db.session.commit()

            if g.admin_authenticated:
                flash("Order created.", "success")
                return redirect(url_for("order_detail", order_id=order.id))
            return render_template("orders/thank_you.html")

        return render_template("orders/new.html", form_data=form_data or {}, form_token=form_token)

    @app.route("/orders/<int:order_id>/edit", methods=["GET", "POST"])
    @require_admin
    def edit_order(order_id: int):
        order = Order.query.filter_by(id=order_id, is_archived=False).first_or_404()
        if request.method == "POST":
            form = request.form
            order.delivery_date = parse_date(form.get("delivery_date")) or order.delivery_date
            order.items_text = form.get("items_text", order.items_text)
            order.notes = form.get("notes", order.notes)
            price_raw = form.get("price_hkd")
            if price_raw:
                try:
                    order.price_hkd = Decimal(price_raw)
                except InvalidOperation:
                    flash("Please enter a valid price.", "error")
                    return render_template("orders/edit.html", order=order)
            else:
                order.price_hkd = None
            db.session.commit()
            flash("Order updated.", "success")
            return redirect(url_for("order_detail", order_id=order.id))
        return render_template("orders/edit.html", order=order)

    @app.route("/clients")
    @require_admin
    def clients_list():
        query = request.args.get("q", "")
        clients_query = Client.query.filter(Client.is_archived.is_(False))
        if query:
            like = f"%{query}%"
            clients_query = clients_query.filter(
                or_(
                    Client.name.ilike(like),
                    Client.email.ilike(like),
                    Client.phone.ilike(like),
                )
            )
        clients = clients_query.order_by(Client.name.asc()).all()
        return render_template("clients/list.html", clients=clients, q=query)

    @app.route("/clients/<int:client_id>")
    @require_admin
    def client_detail(client_id: int):
        client = Client.query.filter_by(id=client_id, is_archived=False).first_or_404()
        orders = (
            Order.query.filter_by(client_id=client.id, is_archived=False)
            .order_by(Order.delivery_date.desc())
            .all()
        )
        return render_template("clients/detail.html", client=client, orders=orders)

    @app.route("/clients/new", methods=["GET", "POST"])
    @require_admin
    def new_client():
        if request.method == "POST":
            form = request.form
            client = Client(
                name=form.get("name"),
                phone=form.get("phone"),
                email=form.get("email"),
                address=form.get("address"),
                notes=form.get("notes"),
            )
            db.session.add(client)
            db.session.commit()
            flash("Client created.", "success")
            return redirect(url_for("clients_list"))
        return render_template("clients/new.html")

    @app.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
    @require_admin
    def edit_client(client_id: int):
        client = Client.query.filter_by(id=client_id, is_archived=False).first_or_404()
        if request.method == "POST":
            form = request.form
            client.name = form.get("name", client.name)
            client.phone = form.get("phone", client.phone)
            client.email = form.get("email", client.email)
            client.address = form.get("address", client.address)
            client.notes = form.get("notes", client.notes)
            db.session.commit()
            flash("Client updated.", "success")
            return redirect(url_for("client_detail", client_id=client.id))
        return render_template("clients/edit.html", client=client)

    @app.route("/clients/<int:client_id>/delete", methods=["POST"])
    @require_admin
    def delete_client(client_id: int):
        client = Client.query.filter_by(id=client_id, is_archived=False).first_or_404()
        client.is_archived = True
        db.session.commit()
        flash("Client archived.", "info")
        return redirect(url_for("clients_list"))

    @app.route("/calendar")
    @require_admin
    def calendar_view():
        orders = (
            Order.query.filter(Order.is_archived.is_(False))
            .order_by(Order.delivery_date.asc())
            .all()
        )
        grouped = {}
        for order in orders:
            grouped.setdefault(order.delivery_date, []).append(order)
        return render_template("calendar.html", grouped=grouped)

    def order_to_ics(order: Order) -> str:
        summary = f"Delivery – {order.client.name}"
        dt = order.delivery_date.strftime("%Y%m%d")
        description_lines = [
            f"Order ID: {order.public_id}",
            f"Items: {order.items_text or 'N/A'}",
            f"Address: {order.client.address or 'N/A'}",
        ]
        description = "\\n".join(description_lines)
        uid = f"kgf-order-{order.id}@kewgardenflowers"
        return (
            "BEGIN:VEVENT\n"
            f"UID:{uid}\n"
            f"SUMMARY:{summary}\n"
            f"DTSTART;VALUE=DATE:{dt}\n"
            f"DESCRIPTION:{description}\n"
            "END:VEVENT\n"
        )

    @app.route("/calendar.ics")
    def calendar_feed():
        orders = Order.query.filter(Order.is_archived.is_(False)).all()
        vevents = "".join(order_to_ics(order) for order in orders)
        ics = (
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "PRODID:-//Kew Garden Flowers//Orders//EN\n"
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n"
            f"X-WR-TIMEZONE:Europe/London\n"
            f"{vevents}END:VCALENDAR\n"
        )
        return Response(ics, content_type="text/calendar")

    @app.route("/export.csv")
    @require_admin
    def export_orders_csv():
        rows = ["Order ID,Client,Delivery Date,Price HKD,Status"]
        orders = Order.query.filter(Order.is_archived.is_(False)).order_by(Order.delivery_date.asc()).all()
        for order in orders:
            rows.append(
                ",".join(
                    [
                        order.public_id,
                        f"{order.client.name}",
                        order.delivery_date.isoformat(),
                        f"{order.price_hkd or ''}",
                        order.status,
                    ]
                )
            )
        csv_content = "\n".join(rows)
        return Response(csv_content, content_type="text/csv")

    @app.route("/clients.csv")
    @require_admin
    def export_clients_csv():
        rows = ["Client ID,Name,Email,Phone,Address"]
        clients = Client.query.filter(Client.is_archived.is_(False)).order_by(Client.name.asc()).all()
        for client in clients:
            rows.append(
                ",".join(
                    [
                        str(client.id),
                        client.name,
                        client.email or "",
                        client.phone or "",
                        (client.address or "").replace(",", ";"),
                    ]
                )
            )
        csv_content = "\n".join(rows)
        return Response(csv_content, content_type="text/csv")

    @app.context_processor
    def inject_globals():
        return {"is_admin": session.get("is_admin", False), "today": datetime.utcnow().date()}

    @app.template_filter("currency")
    def format_currency(value):
        if value is None:
            return "–"
        return f"HK$ {Decimal(value):,.2f}"


__all__ = ["create_app", "db", "Client", "Order", "Config", "compute_next_public_id"]
