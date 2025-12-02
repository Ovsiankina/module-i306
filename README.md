# Fnuc Marty SA

E-commerce platform developed with Python Flask.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Live Project](#live-project)

## Features

- **Shopping cart** with saved state between visits
- **Order management** with proper order processing system
- **User authentication and authorization**
- **Stripe integration** for online payments
- **Custom admin panel** for order processing and item management
- **Item search** with search bar
- **Modern UI** with Bootstrap + custom CSS
- **Responsive interface** for desktop and mobile

## Prerequisites

- [Python](https://www.python.org/) (version 3.7 or higher)
- Stripe API key for payment integration
- [Stripe webhook setup](https://stripe.com/docs/payments/handling-payment-events#install-cli)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/diwash007/Flask-O-shop.git
cd Flask-O-shop
```

### 2. Create a virtual environment

**On Linux/Mac:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**On Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file at the project root based on `env-example.txt`:

```bash
SECRET_KEY=your_secret_key_here
DB_URI="sqlite:///test.db"
EMAIL=your_email@example.com
PASSWORD=your_email_password
STRIPE_PUBLIC=your_stripe_public_key
STRIPE_PRIVATE=your_stripe_private_key
ENDPOINT_SECRET=your_stripe_endpoint_secret
```

**Important:** Set up the Stripe API key first before running the application.

## Usage

### Run the application in production mode

```bash
python -m flask run
```

### Run the application in development mode

**On Linux/Mac:**
```bash
FLASK_DEBUG=1 python -m flask run
```

**On Windows (PowerShell):**
```powershell
$env:FLASK_DEBUG=1; python -m flask run
```

**On Windows (Command Prompt):**
```cmd
set FLASK_DEBUG=1 && python -m flask run
```

**Note:** In `FLASK_DEBUG=1` mode, the application automatically seeds an empty development database, allowing you to get demo items without having to import data manually. A default admin account is also created:
- **Email:** `admin@example.com`
- **Password:** `admin`

### Access the application

Once the application is running, access:
- **Main application:** http://localhost:5000
- **Admin panel:** http://localhost:5000/admin

## Testing

The project includes a test suite with pytest. To run the tests:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_admin_inventory.py
```

### Available tests

- `test_admin_inventory.py` - Tests for admin inventory management
- `test_auto_migrate.py` - Tests for automatic database migration

## Project Structure

```
module-i306/
├── app/                    # Main application
│   ├── admin/             # Admin panel
│   │   ├── forms.py       # Admin forms
│   │   ├── routes.py      # Admin routes
│   │   ├── static/        # Admin static assets
│   │   └── templates/     # Admin templates
│   ├── static/            # Static files (CSS, images)
│   ├── templates/         # HTML templates
│   ├── db_models.py       # Database models
│   ├── forms.py           # Forms
│   ├── funcs.py           # Utility functions
│   └── seed_data.py       # Seed data
├── documentation/         # Project documentation
│   ├── cahier-des-charges.md
│   └── E2E-TESTING.md
├── tests/                 # Automated tests
├── app.py                 # Application entry point
├── requirements.txt       # Python dependencies
├── Pipfile               # Pipenv dependency manager
└── README.md             # This file
```

## Documentation

- [Requirements document](./documentation/cahier-des-charges.md)
- [End-to-end testing](./documentation/E2E-TESTING.md)

## Live Project

Deployed version available at: <https://flaskoshop.gilobyte.com>

## License

[To be defined]

## Authors

Fnuc Marty SA
