from app import (
	_auto_migrate_dev_database,
	app as flask_app,
	configure_app,
	db,
)
from app.db_models import Inventory, Item
from app.seed_data import DEFAULT_ITEMS


def _prepare_empty_db(tmp_path):
	test_db = tmp_path / "auto_seed.sqlite"
	configure_app(
		flask_app,
		{
			"TESTING": True,
			"SQLALCHEMY_DATABASE_URI": f"sqlite:///{test_db}",
			"ADMIN_API_TOKEN": "test-token",
			"WTF_CSRF_ENABLED": False,
			"MAIL_SUPPRESS_SEND": True,
		},
	)
	with flask_app.app_context():
		db.session.remove()
		db.drop_all()
		db.create_all()
	return test_db


def test_auto_migrate_seeds_items_when_db_empty(tmp_path, monkeypatch):
	_prepare_empty_db(tmp_path)
	monkeypatch.setenv("FLASK_DEBUG", "1")

	with flask_app.app_context():
		_auto_migrate_dev_database()
		assert Item.query.count() == len(DEFAULT_ITEMS)
		assert Inventory.query.count() == len(DEFAULT_ITEMS)


def test_auto_migrate_adds_inventory_for_existing_items(tmp_path, monkeypatch):
	_prepare_empty_db(tmp_path)
	monkeypatch.setenv("FLASK_DEBUG", "1")

	with flask_app.app_context():
		item = Item(
			name="Legacy item",
			price=10.0,
			category="Misc",
			image="/static/uploads/legacy.jpg",
			details="Legacy data without inventory",
			price_id="legacy-price",
		)
		db.session.add(item)
		db.session.commit()
		assert Inventory.query.count() == 0

		_auto_migrate_dev_database()
		db.session.refresh(item)
		assert Inventory.query.count() == 1
		assert item.inventory.is_published is True
