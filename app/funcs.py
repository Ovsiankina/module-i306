import datetime
import os
import secrets
from functools import wraps

from flask import abort, current_app, redirect, render_template, request, url_for
from itsdangerous import URLSafeTimedSerializer
from flask_login import current_user
from flask_mail import Mail, Message
from dotenv import load_dotenv
from .db_models import Order, Ordered_item, db, User


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
		sender=("Flask-O-shop Email Confirmation", sender_email),
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
