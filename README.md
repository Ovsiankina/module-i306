# Fnuc Marty SA

Plateforme de commerce électronique développée avec Python Flask

## usage

```bash
# Setup up the API key for stripe first
python -m flask run

# Run without stripe in DEBUG mode
FLASK_DEBUG=1 python -m flask run

# When running with FLASK_DEBUG=1 the app seeds an empty dev DB automatically,
# so you can get demo items without having to import data manually.
```

**Features:**

- Cart, orders, and items feature with proper order processing system
- Proper user authentication and authorization
- Stripe Payment Integration
- Custom admin panel for order processing and managing items
- Item Search feature
- Boostrap + custom CSS UI

## Prerequisties

- [Python](https://www.python.org/)
- Stripe API key for Stripe Payment Integration
- [Stripe webhook setup](https://stripe.com/docs/payments/handling-payment-events#install-cli)

## Installation

Downloading files:

```bash
git clone https://github.com/diwash007/Flask-O-shop.git
```

Installing requirements:

```bash
python -m venv .venv`
source .venv/bin/activate # on linux
pip install -r requirements.txt
```

## Live Project

<https://flaskoshop.gilobyte.com>
