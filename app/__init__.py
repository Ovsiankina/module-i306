import json
import os
from datetime import datetime

try:
    import stripe  # optional in development
except Exception:  # pragma: no cover
    stripe = None
from dotenv import load_dotenv
from flask import Flask, abort, flash, make_response, redirect, render_template, request, url_for
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
from .db_models import Inventory, Item, User, db
from .forms import LoginForm, RegisterForm
from .funcs import (
	add_to_cart_cookie,
	fulfill_order,
    get_cart_combined,
    get_cart_from_cookies,
    get_cart_from_localstorage,
    get_cart_items_count,
    mail,
    remove_from_cart_cookie,
    save_cart_to_cookies,
	send_confirmation_email,
	sync_cart_cookie_to_db,
	sync_localstorage_to_cookies,
)
from .seed_data import DEFAULT_ITEMS

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


def _debug_seeding_enabled() -> bool:
	debug_env = os.getenv("FLASK_DEBUG", "").lower()
	if debug_env in {"1", "true", "yes", "on"}:
		return True
	return bool(app.config.get("DEV_MODE"))


def _seed_default_inventory():
	for item_data in DEFAULT_ITEMS:
		inventory_data = item_data.get("inventory", {})
		item = Item(
			name=item_data["name"],
			price=item_data["price"],
			category=item_data["category"],
			image=item_data["image"],
			details=item_data["details"],
			price_id=item_data["price_id"],
		)
		db.session.add(item)
		db.session.flush()

		db.session.add(
			Inventory(
				item=item,
				stock_quantity=inventory_data.get("stock_quantity", 0),
				low_stock_threshold=inventory_data.get("low_stock_threshold", 0),
				is_published=inventory_data.get("is_published", True),
			)
		)


def _seed_default_admin():
	"""Create a default admin user if no admin exists. Returns True if admin was created."""
	# Check if any admin user already exists
	if User.query.filter_by(admin=True).first():
		return False
	
	# Create default admin user
	admin_user = User(
		name="Admin",
		email="admin@example.com",
		password=generate_password_hash("admin", method="pbkdf2:sha256", salt_length=8),
		phone="0000000000",
		admin=True,
		email_confirmed=True,
	)
	db.session.add(admin_user)
	return True


def _auto_migrate_dev_database():
	if not _debug_seeding_enabled():
		return

	added = False
	# Ensure every legacy item created before inventory shipped receives an inventory row.
	for item in Item.query.filter(~Item.inventory.has()).all():
		db.session.add(
			Inventory(
				item=item,
				stock_quantity=0,
				low_stock_threshold=0,
				is_published=True,
			)
		)
		added = True

	if Item.query.count() == 0:
		_seed_default_inventory()
		added = True

	# Create default admin user if none exists
	admin_created = _seed_default_admin()
	if admin_created:
		added = True

	if added:
		db.session.commit()


with app.app_context():
	db.create_all()
	_auto_migrate_dev_database()


@app.context_processor
def inject_now():
    """sends datetime to templates as 'now' and cart items count"""
    cart_count = get_cart_items_count()
    return {"now": datetime.utcnow(), "cart_items_count": cart_count}


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
            # Synchroniser le panier cookie vers la DB
            if sync_cart_cookie_to_db(user):
                # Si un panier a été synchronisé, supprimer le cookie et informer l'utilisateur
                flash("Votre panier a été synchronisé avec votre compte!", "success")
                response = make_response(redirect(url_for("home")))
                response.set_cookie('cart', '', expires=0)
                return response
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
    item = Item.query.get(id)
    if not item:
        flash("Item not found!", "error")
        return redirect(url_for("home"))
    
    if request.method == "POST":
        quantity = request.form["quantity"]
        
        if current_user.is_authenticated:
            # Utilisateur connecté : utiliser la DB
            current_user.add_to_cart(id, quantity)
            flash(
                f"""{item.name} successfully added to the <a href=cart>cart</a>.<br> <a href={url_for("cart")}>view cart!</a>""",
                "success",
            )
            return redirect(url_for("home"))
        else:
            # Utilisateur non connecté : utiliser les cookies (ou localStorage si cookies désactivés)
            cart = add_to_cart_cookie(id, quantity)
            # Si localStorage est présent, le fusionner
            cart_localstorage = get_cart_from_localstorage()
            if cart_localstorage:
                from .funcs import merge_carts
                cart = merge_carts(cart, cart_localstorage)
            
            response = make_response(redirect(url_for("home")))
            # Essayer de sauvegarder dans les cookies
            try:
                response = save_cart_to_cookies(response, cart)
            except:
                # Si les cookies ne fonctionnent pas, on laisse le client gérer avec localStorage
                pass
            flash(
                f"""{item.name} successfully added to the <a href=cart>cart</a>.<br> <a href={url_for("cart")}>view cart!</a>""",
                "success",
            )
            return response


@app.route("/cart")
def cart():
    price = 0
    price_ids = []
    items = []
    quantity = []
    
    if current_user.is_authenticated:
        # Utilisateur connecté : lire depuis la DB
        for cart in current_user.cart:
            items.append(cart.item)
            quantity.append(cart.quantity)
            price_id_dict = {
                "price": cart.item.price_id,
                "quantity": cart.quantity,
            }
            price_ids.append(price_id_dict)
            price += cart.item.price * cart.quantity
    else:
        # Utilisateur non connecté : lire depuis les cookies ou localStorage
        cart_data = get_cart_combined()
        for itemid_str, qty in cart_data.items():
            item = Item.query.get(int(itemid_str))
            if item:  # Vérifier que l'article existe toujours
                items.append(item)
                quantity.append(qty)
                price_id_dict = {
                    "price": item.price_id,
                    "quantity": qty,
                }
                price_ids.append(price_id_dict)
                price += item.price * qty
    
    return render_template(
        "cart.html", items=items, price=price, price_ids=price_ids, quantity=quantity
    )


@app.route("/orders")
@login_required
def orders():
    return render_template("orders.html", orders=current_user.orders)


@app.route("/remove/<id>/<quantity>")
def remove(id, quantity):
    if current_user.is_authenticated:
        # Utilisateur connecté : utiliser la DB
        current_user.remove_from_cart(id, quantity)
        return redirect(url_for("cart"))
    else:
        # Utilisateur non connecté : utiliser les cookies (ou localStorage)
        cart = remove_from_cart_cookie(id, quantity)
        # Si localStorage est présent, le fusionner
        cart_localstorage = get_cart_from_localstorage()
        if cart_localstorage:
            from .funcs import merge_carts
            cart = merge_carts(cart, cart_localstorage)
        
        response = make_response(redirect(url_for("cart")))
        # Essayer de sauvegarder dans les cookies
        try:
            response = save_cart_to_cookies(response, cart)
        except:
            # Si les cookies ne fonctionnent pas, on laisse le client gérer avec localStorage
            pass
        return response


@app.route("/item/<int:id>")
def item(id):
    item = Item.query.get(id)
    return render_template("item.html", item=item)


@app.route("/cgu")
def cgu():
    """Page des conditions générales d'utilisation"""
    return render_template("cgu.html")


@app.route("/spydeweb")
def spydeweb():
    """Page de présentation de Spy de web"""
    return render_template("spydeweb.html")


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
    # Nécessite une authentification pour passer à la caisse
    if not current_user.is_authenticated:
        flash(
            f'Vous devez vous connecter pour passer à la caisse!<br> <a href={url_for("login")}>Connexion</a>',
            "error",
        )
        return redirect(url_for("login"))
    
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


# API endpoints pour localStorage
@app.route("/api/sync-cart", methods=["POST"])
def api_sync_cart():
    """Endpoint API pour synchroniser le panier localStorage avec les cookies"""
    if current_user.is_authenticated:
        return {"error": "User is authenticated, use DB"}, 400
    
    try:
        cart_data = request.get_json()
        if not cart_data:
            cart_data = {}
        
        # Synchroniser localStorage vers cookies
        merged_cart = sync_localstorage_to_cookies(cart_data)
        
        # Sauvegarder dans les cookies
        response = make_response(json.dumps({"success": True, "cart": merged_cart}))
        response.headers["Content-Type"] = "application/json"
        response = save_cart_to_cookies(response, merged_cart)
        
        return response
    except Exception as e:
        return json.dumps({"error": str(e)}), 400


@app.route("/api/get-cart", methods=["GET"])
def api_get_cart():
    """Endpoint API pour récupérer le panier (cookies ou localStorage)"""
    if current_user.is_authenticated:
        # Retourner le panier depuis la DB
        cart_items = {}
        for cart in current_user.cart:
            cart_items[str(cart.itemid)] = cart.quantity
        return json.dumps({"cart": cart_items})
    else:
        # Retourner le panier depuis cookies ou localStorage
        cart = get_cart_combined()
        return json.dumps({"cart": cart})
