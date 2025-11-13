import os
from pathlib import Path

import pytest

from app import app as flask_app
from app import configure_app, db


@pytest.fixture(scope="session")
def _test_db_path():
	db_file = Path("tests/test_admin.sqlite")
	if db_file.exists():
		db_file.unlink()
	yield db_file
	if db_file.exists():
		db_file.unlink()


@pytest.fixture
def app(_test_db_path):
	configure_app(
		flask_app,
		{
			"TESTING": True,
			"SQLALCHEMY_DATABASE_URI": f"sqlite:///{_test_db_path}",
			"ADMIN_API_TOKEN": "test-token",
			"WTF_CSRF_ENABLED": False,
			"MAIL_SUPPRESS_SEND": True,
		},
	)
	with flask_app.app_context():
		db.session.remove()
		db.drop_all()
		db.create_all()
		yield flask_app
		db.session.remove()
		db.drop_all()


@pytest.fixture
def client(app):
	return app.test_client()


@pytest.fixture
def admin_headers():
	return {"Authorization": "Bearer test-token", "Accept": "application/json"}
