# End-to-End Test Checklist

1. **Install & bootstrap**
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
   - `cp env-example.txt .env` and fill credentials or set `STRIPE_DISABLED=1`.

2. **Reset database**
   - `python -m flask shell -c "from app import db; db.drop_all(); db.create_all()"`
   - Optionally load fixtures with a short script to create demo users/items.

3. **Run automated suite**
   - `python -m pytest` (ensures inventory CRUD, logging, and token/auth guards stay healthy).

4. **Start application**
   - `FLASK_DEBUG=0 ADMIN_API_TOKEN=e2e-token python -m flask run --port 5050`
   - Verify `/` renders without 500s and shows only published items.

5. **Exercise admin APIs**
   - `./tests/integration_admin.sh` (uses curl + SQLite scratch DB for API smoke checks).
   - Inspect `/tmp/integration_flask.log` for errors.

6. **Manual admin flows**
   - Browse to `http://127.0.0.1:5050/login`, authenticate as admin, create/edit/delete products, adjust stock, and download the CSV export.

7. **Checkout happy path**
   - As a customer: register/login, add items to cart, place an order (use Stripe test keys; monitor console for confirmation).

8. **Regression sweep**
   - Confirm search, low-stock banners on `/admin`, and storefront visibility toggles.
