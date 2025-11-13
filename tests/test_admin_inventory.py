from app.db_models import InventoryLog, Item


def _create_item(client, admin_headers, **overrides):
	payload = {
		"name": "Test Item",
		"price": 19.99,
		"category": "Books",
		"details": "A test inventory item",
		"price_id": "price_test",
		"stock_quantity": 10,
		"low_stock_threshold": 3,
		"is_published": True,
	}
	payload.update(overrides)
	response = client.post("/admin/api/items", json=payload, headers=admin_headers)
	assert response.status_code == 201, response.get_json()
	return response.get_json()


def test_admin_api_requires_token(client):
	response = client.get("/admin/api/items", headers={"Accept": "application/json"})
	assert response.status_code == 401


def test_create_item_creates_inventory_and_logs(app, client, admin_headers):
	result = _create_item(client, admin_headers, stock_quantity=5, low_stock_threshold=2)
	assert result["stock_quantity"] == 5
	assert result["low_stock_threshold"] == 2

	with app.app_context():
		item = Item.query.get(result["id"])
		assert item is not None
		assert item.inventory is not None
		assert item.inventory.stock_quantity == 5
		assert item.inventory.low_stock_threshold == 2

		logs = InventoryLog.query.filter_by(item_id=item.id).all()
		field_names = {log.field_name for log in logs}
		assert "stock_quantity" in field_names
		assert "is_published" in field_names


def test_patch_item_updates_fields_and_logging(app, client, admin_headers):
	result = _create_item(client, admin_headers)
	item_id = result["id"]

	update_response = client.patch(
		f"/admin/api/items/{item_id}",
		json={
			"price": 29.99,
			"stock_quantity": 4,
			"low_stock_threshold": 5,
			"is_published": False,
		},
		headers=admin_headers,
	)
	assert update_response.status_code == 200
	body = update_response.get_json()
	assert body["price"] == 29.99
	assert body["stock_quantity"] == 4
	assert body["low_stock_threshold"] == 5
	assert body["is_published"] is False

	with app.app_context():
		item = Item.query.get(item_id)
		assert item.price == 29.99
		assert item.inventory.stock_quantity == 4
		assert item.inventory.low_stock_threshold == 5
		assert item.inventory.is_published is False

		logs = InventoryLog.query.filter_by(item_id=item.id).order_by(InventoryLog.created_at.asc()).all()
		field_names = [log.field_name for log in logs]
		assert "price" in field_names
		assert "stock_quantity" in field_names
		assert "low_stock_threshold" in field_names
		assert "is_published" in field_names


def test_adjust_stock_delta(app, client, admin_headers):
	result = _create_item(client, admin_headers, stock_quantity=2)
	item_id = result["id"]

	response = client.post(
		f"/admin/api/items/{item_id}/stock",
		json={"delta": 3, "note": "Restock"},
		headers=admin_headers,
	)
	assert response.status_code == 200
	body = response.get_json()
	assert body["stock_quantity"] == 5

	with app.app_context():
		item = Item.query.get(item_id)
		assert item.inventory.stock_quantity == 5
		latest_log = InventoryLog.query.filter_by(item_id=item.id).order_by(InventoryLog.created_at.desc()).first()
		assert latest_log is not None
		assert latest_log.note == "Restock"
		assert latest_log.new_value == "5"


def test_low_stock_flag_and_export(client, admin_headers):
	result = _create_item(client, admin_headers, stock_quantity=1, low_stock_threshold=2)
	item_id = result["id"]

	items_response = client.get("/admin/api/items", headers=admin_headers)
	assert items_response.status_code == 200
	items = items_response.get_json()
	item = next(obj for obj in items if obj["id"] == item_id)
	assert item["low_stock"] is True

	export_response = client.get("/admin/api/inventory/export", headers=admin_headers)
	assert export_response.status_code == 200
	assert "text/csv" in export_response.headers["Content-Type"]
	assert "inventory.csv" in export_response.headers["Content-Disposition"]
	assert str(item_id) in export_response.data.decode()


def test_create_item_rejects_negative_stock(client, admin_headers):
	response = client.post(
		"/admin/api/items",
		json={
			"name": "Invalid",
			"price": 5.0,
			"category": "Test",
			"details": "Invalid stock",
			"price_id": "price_invalid",
			"stock_quantity": -1,
		},
		headers=admin_headers,
	)
	assert response.status_code == 400
	assert "non-negative integer" in response.get_json()["error"]


def test_home_filters_unpublished_items(app, client, admin_headers):
	_create_item(client, admin_headers, name="Visible Item", is_published=True)
	_create_item(client, admin_headers, name="Hidden Item", is_published=False)

	response = client.get("/")
	assert response.status_code == 200
	body = response.get_data(as_text=True)
	assert "Visible Item" in body
	assert "Hidden Item" not in body


def test_patch_item_without_image_preserves_existing_image(app, client, admin_headers):
	result = _create_item(client, admin_headers, image="/static/uploads/original.png")
	item_id = result["id"]

	response = client.patch(
		f"/admin/api/items/{item_id}",
		json={
			"name": "Updated Name",
			"details": "Updated details",
			"price": 19.99,
		},
		headers=admin_headers,
	)
	assert response.status_code == 200

	with app.app_context():
		item = Item.query.get(item_id)
		assert item.name == "Updated Name"
		assert item.image == "/static/uploads/original.png"
