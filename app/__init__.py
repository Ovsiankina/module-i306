import json
import os
from datetime import datetime

try:
    import stripe  # optional in development
except Exception:  # pragma: no cover
    stripe = None
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_bootstrap import Bootstrap
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from .admin.routes import admin
from .db_models import Item, User, db
from .forms import LoginForm, RegisterForm
from .funcs import fulfill_order, mail, send_confirmation_email

load_dotenv()


def configure_app(app: Flask, config_overrides: dict | None = None) -> Flask:
    """Configure app defaults with optional overrides (used by tests)."""
    config_overrides = config_overrides or {}

    dev_mode = config_overrides.get("DEV_MODE")
    if dev_mode is None:
        dev_mode = (
            os.getenv("FLASK_ENV") == "development"
            or os.getenv("FLASK_DEBUG") in ("1", "true", "True")
            or os.getenv("DEBUG") in ("1", "true", "True")
            or config_overrides.get("TESTING", False)
        )

    secret_key = config_overrides.get("SECRET_KEY") or os.getenv("SECRET_KEY")
    if not secret_key and dev_mode:
        secret_key = "dev-secret-key"
    elif not secret_key:
        raise RuntimeError("SECRET_KEY is required. Set it in environment or .env")

    db_uri = config_overrides.get("SQLALCHEMY_DATABASE_URI") or os.getenv("DB_URI")
    if not db_uri and dev_mode:
        base_dir = os.path.dirname(__file__)
        db_uri = "sqlite:///" + os.path.join(base_dir, "test.db")
    elif not db_uri:
        raise RuntimeError("DB_URI is required. Set it in environment or .env")

    mail_username = config_overrides.get("MAIL_USERNAME")
    if mail_username is None:
        mail_username = os.getenv("EMAIL", "")

    mail_password = config_overrides.get("MAIL_PASSWORD")
    if mail_password is None:
        mail_password = os.getenv("PASSWORD", "")

    admin_api_token = config_overrides.get("ADMIN_API_TOKEN")
    if admin_api_token is None:
        admin_api_token = os.getenv("ADMIN_API_TOKEN", "")

    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAIL_USERNAME=mail_username or "",
        MAIL_PASSWORD=mail_password or "",
        MAIL_SERVER="smtp.googlemail.com",
        MAIL_USE_TLS=True,
        MAIL_PORT=587,
        MAIL_SUPPRESS_SEND=bool(dev_mode and (not mail_username or not mail_password)),
        ADMIN_API_TOKEN=admin_api_token or "",
        DEV_MODE=bool(dev_mode),
    )

    if config_overrides:
        app.config.update(config_overrides)

    stripe_key = app.config.get("STRIPE_PRIVATE") or os.getenv("STRIPE_PRIVATE")
    if stripe and stripe_key:
        stripe.api_key = stripe_key
        app.config["STRIPE_DISABLED"] = False
    else:
        app.config["STRIPE_DISABLED"] = True

    return app


app = Flask(__name__)
configure_app(app)
Bootstrap(app)
db.init_app(app)
mail.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
app.register_blueprint(admin)

with app.app_context():
    db.create_all()


@app.context_processor
def inject_now():
    """sends datetime to templates as 'now'"""
    return {"now": datetime.utcnow()}


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route("/")
def home():
    items = Item.query.all()
    visible_items = [
        item for item in items if not getattr(item, "inventory", None) or item.inventory.is_published
    ]
    return render_template("home.html", items=visible_items)


@app.route("/login", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user == None:
            flash(
                f'User with email {email} doesn\'t exist!<br> <a href={url_for("register")}>Register now!</a>',
                "error",
            )
            return redirect(url_for("login"))
        elif check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("home"))
        else:
            flash("Email and password incorrect!!", "error")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)


@app.route("/register", methods=["POST", "GET"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash(
                f"User with email {user.email} already exists!!<br> <a href={url_for('login')}>Login now!</a>",
                "error",
            )
            return redirect(url_for("register"))
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=generate_password_hash(
                form.password.data, method="pbkdf2:sha256", salt_length=8
            ),
            phone=form.phone.data,
        )
        db.session.add(new_user)
        db.session.commit()
        # send_confirmation_email(new_user.email)
        flash("Thanks for registering! You may login now.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/confirm/<token>")
def confirm_email(token):
    try:
        confirm_serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        email = confirm_serializer.loads(
            token, salt="email-confirmation-salt", max_age=3600
        )
    except:
        flash("The confirmation link is invalid or has expired.", "error")
        return redirect(url_for("login"))
    user = User.query.filter_by(email=email).first()
    if user.email_confirmed:
        flash(f"Account already confirmed. Please login.", "success")
    else:
        user.email_confirmed = True
        db.session.add(user)
        db.session.commit()
        flash("Email address successfully confirmed!", "success")
    return redirect(url_for("login"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/resend")
@login_required
def resend():
    send_confirmation_email(current_user.email)
    logout_user()
    flash("Confirmation email sent successfully.", "success")
    return redirect(url_for("login"))


@app.route("/add/<id>", methods=["POST"])
def add_to_cart(id):
    if not current_user.is_authenticated:
        flash(
            f'You must login first!<br> <a href={url_for("login")}>Login now!</a>',
            "error",
        )
        return redirect(url_for("login"))

    item = Item.query.get(id)
    if request.method == "POST":
        quantity = request.form["quantity"]
        current_user.add_to_cart(id, quantity)
        flash(
            f"""{item.name} successfully added to the <a href=cart>cart</a>.<br> <a href={url_for("cart")}>view cart!</a>""",
            "success",
        )
        return redirect(url_for("home"))


@app.route("/cart")
@login_required
def cart():
    price = 0
    price_ids = []
    items = []
    quantity = []
    for cart in current_user.cart:
        items.append(cart.item)
        quantity.append(cart.quantity)
        price_id_dict = {
            "price": cart.item.price_id,
            "quantity": cart.quantity,
        }
        price_ids.append(price_id_dict)
        price += cart.item.price * cart.quantity
    return render_template(
        "cart.html", items=items, price=price, price_ids=price_ids, quantity=quantity
    )


@app.route("/orders")
@login_required
def orders():
    return render_template("orders.html", orders=current_user.orders)


@app.route("/remove/<id>/<quantity>")
@login_required
def remove(id, quantity):
    current_user.remove_from_cart(id, quantity)
    return redirect(url_for("cart"))


@app.route("/item/<int:id>")
def item(id):
    item = Item.query.get(id)
    return render_template("item.html", item=item)


@app.route("/search")
def search():
    query = request.args["query"]
    search = "%{}%".format(query)
    items = Item.query.filter(Item.name.like(search)).all()
    return render_template("home.html", items=items, search=True, query=query)


# stripe stuffs
@app.route("/payment_success")
def payment_success():
    return render_template("success.html")


@app.route("/payment_failure")
def payment_failure():
    return render_template("failure.html")


@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    # In development without Stripe config, disable checkout gracefully
    if app.config.get("STRIPE_DISABLED"):
        flash("Payments are disabled (Stripe not configured).", "error")
        return redirect(url_for("payment_failure"))

    data = json.loads(request.form["price_ids"].replace("'", '"'))
    try:
        checkout_session = stripe.checkout.Session.create(
            client_reference_id=current_user.id,
            line_items=data,
            payment_method_types=[
                "card",
            ],
            mode="payment",
            success_url=url_for("payment_success", _external=True),
            cancel_url=url_for("payment_failure", _external=True),
        )
    except Exception as e:
        return str(e)
    return redirect(checkout_session.url, code=303)


@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    # In development without Stripe config, acknowledge and exit
    if app.config.get("STRIPE_DISABLED"):
        return {}, 200

    if request.content_length > 1024 * 1024:
        print("Request too big!")
        abort(400)

    payload = request.get_data()
    sig_header = request.environ.get("HTTP_STRIPE_SIGNATURE")
    ENDPOINT_SECRET = os.environ.get("ENDPOINT_SECRET")
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, ENDPOINT_SECRET)
    except ValueError as e:
        # Invalid payload
        return {}, 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return {}, 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # Fulfill the purchase...
        fulfill_order(session)

    # Passed signature verification
    return {}, 200
