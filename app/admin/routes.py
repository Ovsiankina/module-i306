import csv
import io
from pathlib import Path
from typing import Any

from flask import (
	Blueprint,
	current_app,
	flash,
	jsonify,
	make_response,
	render_template,
	request,
	url_for,
)
from flask_login import current_user
from werkzeug.utils import redirect, secure_filename

from ..admin.forms import AddItemForm, OrderEditForm
from ..db_models import Inventory, InventoryLog, Item, Order, Ordered_item, User, db
from ..funcs import admin_only


admin = Blueprint("admin", __name__, url_prefix="/admin", static_folder="static", template_folder="templates")

DEFAULT_IMAGE_FILENAME = "uploads/placeholder.png"


def _upload_folder() -> Path:
	base_path = Path(current_app.root_path) / "static" / "uploads"
	base_path.mkdir(parents=True, exist_ok=True)
	return base_path


def _default_image_url() -> str:
	return url_for("static", filename=DEFAULT_IMAGE_FILENAME)


def _save_image(file_storage) -> str | None:
	if not file_storage or not getattr(file_storage, "filename", ""):
		return None

	filename = secure_filename(file_storage.filename)
	if not filename:
		return None

	target = _upload_folder() / filename
	file_storage.save(target)
	return url_for("static", filename=f"uploads/{filename}")


def _ensure_inventory(item: Item, defaults: dict[str, Any] | None = None) -> Inventory:
	if item.inventory:
		return item.inventory

	defaults = defaults or {}
	inventory = Inventory(
		item=item,
		stock_quantity=defaults.get("stock_quantity", 0),
		low_stock_threshold=defaults.get("low_stock_threshold", 0),
		is_published=defaults.get("is_published", True),
	)
	db.session.add(inventory)
	db.session.flush()
	return inventory


def _log_inventory_change(item: Item, change_type: str, field_name: str, old_value: Any, new_value: Any, note: str | None = None) -> None:
	log_entry = InventoryLog(
		item_id=item.id,
		user_id=current_user.id if current_user.is_authenticated else None,
		change_type=change_type,
		field_name=field_name,
		old_value=str(old_value) if old_value is not None else None,
		new_value=str(new_value) if new_value is not None else None,
		note=note,
	)
	db.session.add(log_entry)


def _coerce_non_negative_int(value: Any, field_name: str, default: int = 0) -> int:
	if value is None:
		return default
	try:
		int_value = int(value)
	except (TypeError, ValueError) as exc:  # pragma: no cover - defensive branch
		raise ValueError(f"{field_name} must be a non-negative integer") from exc
	if int_value < 0:
		raise ValueError(f"{field_name} must be a non-negative integer")
	return int_value


def _item_to_dict(item: Item) -> dict[str, Any]:
	inventory = item.inventory
	if not inventory:
		return {
			"id": item.id,
			"name": item.name,
			"price": item.price,
			"category": item.category,
			"image": item.image,
			"details": item.details,
			"price_id": item.price_id,
			"stock_quantity": 0,
			"low_stock_threshold": 0,
			"is_published": True,
			"low_stock": False,
		}

	low_stock = inventory.low_stock_threshold is not None and inventory.low_stock_threshold > 0 and inventory.stock_quantity <= inventory.low_stock_threshold
	return {
		"id": item.id,
		"name": item.name,
		"price": item.price,
		"category": item.category,
		"image": item.image,
		"details": item.details,
		"price_id": item.price_id,
		"stock_quantity": inventory.stock_quantity,
		"low_stock_threshold": inventory.low_stock_threshold,
		"is_published": inventory.is_published,
		"low_stock": low_stock,
	}


@admin.route("/")
@admin_only
def dashboard():
	from datetime import datetime, timedelta
	from sqlalchemy import func
	
	# Get all orders
	all_orders = Order.query.all()
	orders_query = Order.query.order_by(Order.date.desc()).limit(10).all()
	
	# Calculate total for each order
	orders = []
	for order in orders_query:
		order_total = sum(ordered_item.item.price * ordered_item.quantity for ordered_item in order.items)
		orders.append({
			"order": order,
			"total": order_total
		})
	
	# Calculate statistics
	total_revenue = sum(
		sum(ordered_item.item.price * ordered_item.quantity for ordered_item in order.items)
		for order in all_orders if order.status.lower() != "cancelled"
	)
	total_orders = len(all_orders)
	total_customers = User.query.count()
	total_items = Item.query.count()
	
	# Orders by status
	orders_by_status = {}
	for order in all_orders:
		status = order.status.lower()
		orders_by_status[status] = orders_by_status.get(status, 0) + 1
	
	# Recent orders (last 7 days)
	seven_days_ago = datetime.utcnow() - timedelta(days=7)
	recent_orders_count = Order.query.filter(Order.date >= seven_days_ago).count()
	
	# Recent revenue (last 7 days)
	recent_orders = Order.query.filter(Order.date >= seven_days_ago).all()
	recent_revenue = sum(
		sum(ordered_item.item.price * ordered_item.quantity for ordered_item in order.items)
		for order in recent_orders if order.status.lower() != "cancelled"
	)
	
	# Low stock items
	low_stock_items = [
		item for item in Item.query.all() 
		if item.inventory and item.inventory.low_stock_threshold > 0 
		and item.inventory.stock_quantity <= item.inventory.low_stock_threshold
	]
	
	# Top selling items
	top_items_query = db.session.query(
		Ordered_item.itemid,
		func.sum(Ordered_item.quantity).label('total_quantity')
	).group_by(Ordered_item.itemid).order_by(func.sum(Ordered_item.quantity).desc()).limit(5).all()
	
	top_items = []
	for item_id, quantity in top_items_query:
		item = Item.query.get(item_id)
		if item:
			top_items.append({"item": item, "quantity": quantity})
	
	# Orders per day (last 7 days)
	orders_per_day = []
	for i in range(6, -1, -1):
		day = datetime.utcnow() - timedelta(days=i)
		day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
		day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
		count = Order.query.filter(Order.date >= day_start, Order.date <= day_end).count()
		orders_per_day.append({
			"date": day.strftime("%Y-%m-%d"),
			"day": day.strftime("%a"),
			"count": count
		})
	
	return render_template(
		"admin/home.html",
		orders=orders,
		low_stock_items=low_stock_items,
		total_revenue=total_revenue,
		total_orders=total_orders,
		total_customers=total_customers,
		total_items=total_items,
		orders_by_status=orders_by_status,
		recent_orders_count=recent_orders_count,
		recent_revenue=recent_revenue,
		top_items=top_items,
		orders_per_day=orders_per_day,
	)


@admin.route("/items")
@admin_only
def items():
	items = Item.query.all()
	payload = [_item_to_dict(item) for item in items]
	if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
		return jsonify(payload)

	return render_template("admin/items.html", items=items, inventory=payload)


@admin.route("/add", methods=["POST", "GET"])
@admin_only
def add():
	form = AddItemForm()

	if form.validate_on_submit():
		image = _save_image(form.image.data) or _default_image_url()
		item = Item(
			name=form.name.data,
			price=form.price.data,
			category=form.category.data,
			details=form.details.data,
			image=image,
			price_id=form.price_id.data,
		)
		db.session.add(item)
		db.session.flush()

		inventory = _ensure_inventory(
			item,
			{
				"stock_quantity": form.stock_quantity.data,
				"low_stock_threshold": form.low_stock_threshold.data or 0,
				"is_published": form.is_published.data,
			},
		)
		_log_inventory_change(
			item,
			"create",
			"stock_quantity",
			old_value=None,
			new_value=inventory.stock_quantity,
			note="Initial stock on item creation",
		)
		_log_inventory_change(
			item,
			"create",
			"is_published",
			old_value=None,
			new_value=inventory.is_published,
		)
		db.session.commit()
		flash(f"{item.name} added successfully!", "success")
		return redirect(url_for("admin.items"))
	return render_template("admin/add.html", form=form)


@admin.route("/edit/<string:type>/<int:item_id>", methods=["POST", "GET"])
@admin_only
def edit(type: str, item_id: int):
	if type == "item":
		item = Item.query.get_or_404(item_id)
		inventory = item.inventory or Inventory(stock_quantity=0, low_stock_threshold=0, is_published=True, item=item)
		if not item.inventory:
			db.session.add(inventory)
			db.session.flush()

		form = AddItemForm(
			name=item.name,
			price=item.price,
			category=item.category,
			details=item.details,
			price_id=item.price_id,
			stock_quantity=inventory.stock_quantity,
			low_stock_threshold=inventory.low_stock_threshold,
			is_published=inventory.is_published,
		)
		if request.method == "POST" and form.validate_on_submit():
			original = _item_to_dict(item)

			item.name = form.name.data
			item.price = form.price.data
			item.category = form.category.data
			item.details = form.details.data
			item.price_id = form.price_id.data

			new_image = _save_image(form.image.data)
			if new_image:
				item.image = new_image

			if inventory.stock_quantity != form.stock_quantity.data:
				_log_inventory_change(
					item,
					"update",
					"stock_quantity",
					old_value=inventory.stock_quantity,
					new_value=form.stock_quantity.data,
				)
				inventory.stock_quantity = form.stock_quantity.data

			new_threshold = form.low_stock_threshold.data or 0
			if inventory.low_stock_threshold != new_threshold:
				_log_inventory_change(
					item,
					"update",
					"low_stock_threshold",
					old_value=inventory.low_stock_threshold,
					new_value=new_threshold,
				)
				inventory.low_stock_threshold = new_threshold

			if inventory.is_published != bool(form.is_published.data):
				_log_inventory_change(
					item,
					"update",
					"is_published",
					old_value=inventory.is_published,
					new_value=bool(form.is_published.data),
				)
				inventory.is_published = bool(form.is_published.data)

			if original["price"] != item.price:
				_log_inventory_change(
					item,
					"update",
					"price",
					old_value=original["price"],
					new_value=item.price,
				)

			db.session.commit()
			flash(f"{item.name} updated successfully!", "success")
			return redirect(url_for("admin.items"))

	elif type == "order":
		order = Order.query.get_or_404(item_id)
		form = OrderEditForm(status=order.status)
		if form.validate_on_submit():
			order.status = form.status.data
			db.session.commit()
			return redirect(url_for("admin.dashboard"))
	else:
		flash("Unknown edit type", "error")
		return redirect(url_for("admin.dashboard"))

	return render_template("admin/add.html", form=form)


@admin.route("/delete/<int:item_id>", methods=["POST", "GET"])
@admin_only
def delete(item_id: int):
	item = Item.query.get_or_404(item_id)
	_log_inventory_change(
		item,
		"delete",
		"item",
		old_value=item.name,
		new_value=None,
		note="Item deleted via admin.",
	)
	db.session.delete(item)
	db.session.commit()
	flash(f"{item.name} deleted successfully", "error")
	return redirect(url_for("admin.items"))


@admin.route("/api/items", methods=["GET", "POST"])
@admin_only
def api_items():
	if request.method == "GET":
		items = Item.query.all()
		return jsonify([_item_to_dict(item) for item in items])

	payload = request.get_json(silent=True) or {}
	required_fields = {"name", "price", "category", "details", "price_id"}
	missing = sorted(field for field in required_fields if field not in payload)
	if missing:
		return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

	image_path = payload.get("image")
	if not image_path:
		image_path = _default_image_url()

	item = Item(
		name=payload["name"],
		price=payload["price"],
		category=payload["category"],
		details=payload["details"],
		image=image_path,
		price_id=payload["price_id"],
	)
	db.session.add(item)
	db.session.flush()

	try:
		stock_quantity = _coerce_non_negative_int(payload.get("stock_quantity"), "stock_quantity")
		low_stock_threshold = _coerce_non_negative_int(payload.get("low_stock_threshold"), "low_stock_threshold")
	except ValueError as exc:
		db.session.rollback()
		return jsonify({"error": str(exc)}), 400

	inventory = _ensure_inventory(
		item,
		{
			"stock_quantity": stock_quantity,
			"low_stock_threshold": low_stock_threshold,
			"is_published": payload.get("is_published", True),
		},
	)
	_log_inventory_change(
		item,
		"create",
		"stock_quantity",
		old_value=None,
		new_value=inventory.stock_quantity,
			note=payload.get("note", "Created via API"),
		)
	_log_inventory_change(
		item,
		"create",
		"is_published",
		old_value=None,
		new_value=inventory.is_published,
	)
	if inventory.low_stock_threshold:
		_log_inventory_change(
			item,
			"create",
			"low_stock_threshold",
			old_value=None,
			new_value=inventory.low_stock_threshold,
		)
	db.session.commit()
	return jsonify(_item_to_dict(item)), 201


@admin.route("/api/items/<int:item_id>", methods=["PATCH", "DELETE"])
@admin_only
def api_item_detail(item_id: int):
	item = Item.query.get_or_404(item_id)

	if request.method == "DELETE":
		_log_inventory_change(
			item,
			"delete",
			"item",
			old_value=item.name,
			new_value=None,
			note="Item deleted via API.",
		)
		db.session.delete(item)
		db.session.commit()
		return jsonify({"status": "deleted", "id": item_id})

	payload = request.get_json(silent=True) or {}
	inventory = _ensure_inventory(item)
	before = _item_to_dict(item)

	if "name" in payload:
		item.name = payload["name"]
	if "price" in payload:
		new_price = payload["price"]
		if new_price != before["price"]:
			_log_inventory_change(item, "update", "price", old_value=before["price"], new_value=new_price)
		item.price = new_price
	if "category" in payload:
		item.category = payload["category"]
	if "details" in payload:
		item.details = payload["details"]
	if "price_id" in payload:
		item.price_id = payload["price_id"]
	if "image" in payload:
		item.image = payload["image"]
	if "stock_quantity" in payload:
		try:
			new_stock = _coerce_non_negative_int(payload["stock_quantity"], "stock_quantity")
		except ValueError as exc:
			return jsonify({"error": str(exc)}), 400
		if new_stock != inventory.stock_quantity:
			_log_inventory_change(
				item,
				"update",
				"stock_quantity",
				old_value=inventory.stock_quantity,
				new_value=new_stock,
				note=payload.get("note"),
			)
			inventory.stock_quantity = new_stock
	if "low_stock_threshold" in payload:
		try:
			new_threshold = _coerce_non_negative_int(payload["low_stock_threshold"], "low_stock_threshold")
		except ValueError as exc:
			return jsonify({"error": str(exc)}), 400
		if new_threshold != inventory.low_stock_threshold:
			_log_inventory_change(
				item,
				"update",
				"low_stock_threshold",
				old_value=inventory.low_stock_threshold,
				new_value=new_threshold,
			)
			inventory.low_stock_threshold = new_threshold
	if "is_published" in payload:
		new_published = bool(payload["is_published"])
		if new_published != inventory.is_published:
			_log_inventory_change(
				item,
				"update",
				"is_published",
				old_value=inventory.is_published,
				new_value=new_published,
			)
			inventory.is_published = new_published

	db.session.commit()
	return jsonify(_item_to_dict(item))


@admin.route("/api/items/<int:item_id>/stock", methods=["POST"])
@admin_only
def api_adjust_stock(item_id: int):
	item = Item.query.get_or_404(item_id)
	inventory = _ensure_inventory(item)
	payload = request.get_json(silent=True) or {}

	if "delta" not in payload and "quantity" not in payload:
		return jsonify({"error": "Provide either 'delta' or 'quantity' in payload"}), 400

	note = payload.get("note")
	if "delta" in payload:
		try:
			delta = int(payload["delta"])
		except (TypeError, ValueError):
			return jsonify({"error": "delta must be an integer"}), 400
		new_quantity = inventory.stock_quantity + delta
	else:
		try:
			new_quantity = int(payload["quantity"])
		except (TypeError, ValueError):
			return jsonify({"error": "quantity must be an integer"}), 400

	if new_quantity < 0:
		return jsonify({"error": "Resulting quantity cannot be negative"}), 400

	if new_quantity != inventory.stock_quantity:
		_log_inventory_change(
			item,
			"adjust",
			"stock_quantity",
			old_value=inventory.stock_quantity,
			new_value=new_quantity,
			note=note or ("Delta update" if "delta" in payload else "Quantity override"),
		)
		inventory.stock_quantity = new_quantity
	db.session.commit()
	return jsonify(_item_to_dict(item))


@admin.route("/api/inventory/export", methods=["GET"])
@admin_only
def api_export_inventory():
	items = Item.query.all()
	output = io.StringIO()
	writer = csv.writer(output)
	writer.writerow(["id", "name", "price", "stock_quantity", "low_stock_threshold", "is_published"])
	for item in items:
		inventory = item.inventory or Inventory(stock_quantity=0, low_stock_threshold=0, is_published=True, item=item)
		if not item.inventory:
			db.session.add(inventory)
			db.session.flush()
		writer.writerow(
			[
				item.id,
				item.name,
				item.price,
				inventory.stock_quantity,
				inventory.low_stock_threshold,
				inventory.is_published,
			]
		)
	response = make_response(output.getvalue())
	response.headers["Content-Disposition"] = "attachment; filename=inventory.csv"
	response.headers["Content-Type"] = "text/csv"
	db.session.commit()
	return response
