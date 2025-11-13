# Repository Guidelines

## Project Structure & Module Organization
- `app/` bundles the Flask app: `__init__.py` wires extensions/routes, `db_models.py` defines SQLAlchemy models, `funcs.py` hosts mail and order helpers.
- `app/admin/` isolates the admin blueprint with its own templates/static assets; storefront templates live in `app/templates/`, shared CSS/JS in `app/static/`.
- `documentation/` stores functional specs, `env-example.txt` lists required secrets, and the Heroku-style `Procfile` runs `gunicorn app:app` in production.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create a local virtual environment.
- `pip install -r requirements.txt`: sync dependencies with production.
- `cp env-example.txt .env` then fill Stripe, database, and mail values before running the app.
- `FLASK_DEBUG=1 python -m flask run`: launch the dev server with Stripe auto-disabled for quick checks.
- `python -m flask run` (or `gunicorn app:app`): run with full config to mirror staging/Procfile behavior.

## Coding Style & Naming Conventions
- Target Python 3.11+, follow PEP 8 with 4-space indenting, `snake_case` for functions, and `PascalCase` for models and forms.
- Keep view functions slim; move reusable logic into helpers or blueprints (`app/admin/routes.py` shows the pattern).
- Jinja templates inherit from `templates/base.html`; align new static assets under `app/static/<feature>/`.

## Testing Guidelines
- Add automated coverage with `pytest`; place files under `tests/` named `test_<module>.py` and run via `pytest`.
- Mock Stripe calls or set `STRIPE_DISABLED=1` to exercise payment flows without live keys.
- Before each PR, smoke-test registration, checkout, and admin fulfillment using `FLASK_DEBUG=1 python -m flask run`.

## Commit & Pull Request Guidelines
- Follow `<type>: <subject>` commit style already in history (`feat:`, `chore:`, `docs:`) and keep subjects imperative.
- Each PR should summarize the change, note config/env impacts, and attach UI screenshots when relevant.
- Ensure migrations or seed updates are documented; never commit `.env` or other secrets.

## Agent Tasks
- **David**
  - [x] Mettre en place un tableau de bord `/admin` protégé (authentification + rôle administrateur).
  - [x] Implémenter le CRUD produits (titre, description, prix, images, statut de publication).
  - [x] Gérer les stocks avec ajustements, seuils d'alerte et export CSV d'inventaire.
  - [x] Journaliser les modifications critiques (prix, quantités) pour audit interne.
  - [x] Documenter et exécuter des tests manuels clés (création article, mise à jour prix, traitement commande) + scripts (`tests/integration_admin.sh`, scénarios pytest).
