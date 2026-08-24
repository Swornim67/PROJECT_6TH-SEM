# Income and Expense Record Keeping System

A Django application based on the supplied entity-relationship diagram. It provides secure user accounts, user-owned income/expense categories, transaction records, monthly category budgets, and financial reports.

## Run locally

The project runs immediately with SQLite (the default):

```bash
python3 manage.py migrate
python3 manage.py runserver
```

Open `http://127.0.0.1:8000/`, register an account, create categories, and begin recording transactions.

## MySQL setup

Install MySQL and create a database called `income_expense`. Install dependencies:

```bash
pip install -r requirements.txt
```

Set the environment variables listed in `.env.example`, then run:

```bash
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py runserver
```

The MySQL connection is enabled automatically when `MYSQL_DATABASE` is set. Django’s built-in admin is available at `/admin/`.

## Data model

- `Category`: user, name, type (income or expense), created date
- `Income`: user, category, amount, currency, description, date, timestamps
- `Expense`: user, category, amount, currency, payment method, description, date, timestamps
- `Budget`: user, expense category, month, amount limit
- `Account`: user-owned cash, bank, wallet, credit, and savings accounts
- `Payee`: reusable merchant or income-source records
- `Tag`: user-owned labels for transaction organization
- `RecurringTransaction`: scheduled income or expense rules linked to a category, with optional account and payee
