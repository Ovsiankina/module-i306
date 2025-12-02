import datetime
import json
import os
import secrets
from functools import wraps

from flask import abort, current_app, redirect, render_template, request, url_for
from dotenv import load_dotenv
from flask_login import current_user
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

from .db_models import Cart, Order, Ordered_item, User, db


load_dotenv()
mail = Mail()

def send_confirmation_email(user_email) -> None:
	"""sends confirmation email (suppressed in dev without mail creds)"""
	secret = current_app.config.get("SECRET_KEY", os.getenv("SECRET_KEY", "dev-secret-key"))
	confirm_serializer = URLSafeTimedSerializer(secret)
	confirm_url = url_for(
						'confirm_email',
						token=confirm_serializer.dumps(user_email,
						salt='email-confirmation-salt'),
						_external=True)
	html = render_template('email_confirmation.html', confirm_url=confirm_url)
	sender_email = current_app.config.get("MAIL_USERNAME", os.getenv("EMAIL", "noreply@example.local"))
	msg = Message(
		'Confirm Your Email Address',
		recipients=[user_email],
		sender=("Fnuc Marty SA - Confirmation Email", sender_email),
		html=html,
	)
	mail.send(msg)

def fulfill_order(session):
	""" Fulfils order on successful payment """

	uid = session['client_reference_id']
	order = Order(uid=uid, date=datetime.datetime.now(), status="processing")
	db.session.add(order)
	db.session.commit()

	current_user = User.query.get(uid)
	for cart in current_user.cart:
		ordered_item = Ordered_item(oid=order.id, itemid=cart.item.id, quantity=cart.quantity)
		db.session.add(ordered_item)
		db.session.commit()
		current_user.remove_from_cart(cart.item.id, cart.quantity)
		db.session.commit()

def admin_only(func):
	"""Decorator for giving access to authorized users only (token or admin session)."""

	@wraps(func)
	def wrapper(*args, **kwargs):
		expected_token = (current_app.config.get("ADMIN_API_TOKEN") or "").strip()
		auth_header = request.headers.get("Authorization", "")
		bearer_token = ""
		if auth_header.lower().startswith("bearer "):
			bearer_token = auth_header.split(" ", 1)[1].strip()

		if bearer_token and expected_token:
			try:
				if secrets.compare_digest(bearer_token, expected_token):
					return func(*args, **kwargs)
			except ValueError:
				# secrets.compare_digest requires same type; fall through to reject
				pass

		if current_user.is_authenticated:
			if current_user.admin:
				return func(*args, **kwargs)
			abort(403)

		if request.accept_mimetypes.accept_html:
			return redirect(url_for("login"))

		abort(401)

	return wrapper


# Fonctions pour gérer le panier dans les cookies
def get_cart_from_cookies():
	"""Récupère le panier depuis les cookies"""
	cart_cookie = request.cookies.get("cart")
	if cart_cookie:
		try:
			return json.loads(cart_cookie)
		except json.JSONDecodeError:
			return {}
	return {}


def save_cart_to_cookies(response, cart_dict):
	"""Sauvegarde le panier dans les cookies"""
	max_age = 30 * 24 * 60 * 60  # expire après 30 jours
	cart_json = json.dumps(cart_dict)
	response.set_cookie("cart", cart_json, max_age=max_age, httponly=True)
	return response


def add_to_cart_cookie(itemid, quantity):
	"""Ajoute un article au panier cookie"""
	cart = get_cart_from_cookies()
	itemid_str = str(itemid)

	if itemid_str in cart:
		cart[itemid_str] += int(quantity)
	else:
		cart[itemid_str] = int(quantity)

	return cart


def remove_from_cart_cookie(itemid, quantity):
	"""Retire un article du panier cookie"""
	cart = get_cart_from_cookies()
	itemid_str = str(itemid)

	if itemid_str in cart:
		current_quantity = cart[itemid_str]
		new_quantity = current_quantity - int(quantity)
		if new_quantity <= 0:
			del cart[itemid_str]
		else:
			cart[itemid_str] = new_quantity

	return cart


def sync_cart_cookie_to_db(user):
	"""Synchronise le panier cookie vers la DB lors de la connexion"""
	cart_cookie = get_cart_from_cookies()

	if not cart_cookie:
		return None

	for itemid_str, quantity in cart_cookie.items():
		itemid = int(itemid_str)
		existing_cart_item = Cart.query.filter_by(itemid=itemid, uid=user.id).first()
		if existing_cart_item:
			existing_cart_item.quantity += int(quantity)
		else:
			cart_item = Cart(itemid=itemid, uid=user.id, quantity=int(quantity))
			db.session.add(cart_item)

	db.session.commit()
	return True


def get_cart_from_localstorage():
	"""Récupère le panier depuis localStorage (envoyé via header ou paramètre)"""
	cart_localstorage = request.headers.get("X-Cart-LocalStorage")
	if not cart_localstorage:
		cart_localstorage = request.args.get("cart_localstorage")

	if cart_localstorage:
		try:
			return json.loads(cart_localstorage)
		except json.JSONDecodeError:
			return {}
	return {}


def get_cart_combined():
	"""Récupère le panier depuis cookies ou localStorage (priorité cookies)"""
	cart = get_cart_from_cookies()
	if not cart:
		cart = get_cart_from_localstorage()
	return cart


def merge_carts(cart1, cart2):
	"""Fusionne deux paniers (additionne les quantités)"""
	merged = cart1.copy()
	for itemid, quantity in cart2.items():
		if itemid in merged:
			merged[itemid] = int(merged[itemid]) + int(quantity)
		else:
			merged[itemid] = int(quantity)
	return merged


def sync_localstorage_to_cookies(cart_localstorage):
	"""Synchronise le panier localStorage vers les cookies"""
	cart_cookie = get_cart_from_cookies()
	return merge_carts(cart_cookie, cart_localstorage)


def get_cart_items_count():
	"""Retourne le nombre total d'articles dans le panier (DB, cookie ou localStorage)"""
	if current_user.is_authenticated:
		total = 0
		for cart_item in current_user.cart:
			total += cart_item.quantity
		return total

	cart = get_cart_combined()
	total = 0
	for quantity in cart.values():
		total += int(quantity)
	return total
