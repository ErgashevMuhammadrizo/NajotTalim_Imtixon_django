# Dashboard API Documentation

## API Endpoints

All endpoints require authentication (`@login_required`). They return JSON responses.

### 1. Dashboard Summary
**Endpoint:** `GET /en/expenses/api/dashboard/summary/`

**Query Parameters:**
- `currency`: UZS, USD, EUR (default: UZS)

**Response:**
```json
{
  "total_income": 25786000.0,
  "total_expense": 200.0,
  "current_balance": 25785800.0,
  "income_change": 100.0,
  "expense_change": 0.0,
  "balance_change": 100.0,
  "currency": "UZS",
  "recent_transactions": [...]
}
```

### 2. Chart Data
**Endpoint:** `GET /en/expenses/api/dashboard/chart-data/`

**Query Parameters:**
- `period`: 7, 30, 90, 365 (days, default: 30)
- `currency`: UZS, USD, EUR (default: UZS)

**Response:**
```json
{
  "labels": ["01-14", "01-15", ...],
  "income_data": [0, 1234000, ...],
  "expense_data": [0, 100, ...],
  "currency": "UZS"
}
```

### 3. Category Statistics
**Endpoint:** `GET /en/expenses/api/dashboard/category-stats/`

**Query Parameters:**
- `period`: month, week, year (default: month)
- `currency`: UZS, USD, EUR (default: UZS)

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Category Name",
    "icon": "fas fa-icon",
    "color": "#3b82f6",
    "total": 1000.0,
    "count": 5,
    "percentage": 50.0
  }
]
```

## Exchange Rates

All internal calculations are done in UZS, then converted to requested currency:

- 1 USD = 12500 UZS
- 1 EUR = 13500 UZS
- 1 CNY = 1740 UZS
- 1 RUB = 130 UZS

## Testing

### Direct Python Test:
```python
from django.test import RequestFactory
from expenses.views import dashboard_summary
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='rizo')

factory = RequestFactory()
request = factory.get('/en/expenses/api/dashboard/summary/?currency=UZS')
request.user = user

response = dashboard_summary(request)
print(response.content)
```

### Browser Test:
1. Login at `/en/users/login/`
2. Visit `/en/dashboard/`
3. Open Developer Tools (F12)
4. Check Console for any JavaScript errors
5. Check Network tab to see API calls and responses

## Dashboard Features

- **Real-time Currency Switching**: Click USD/EUR buttons to see amounts in different currencies
- **Time Period Selection**: 7 days, 30 days, 3 months, 1 year chart views
- **Transaction Filtering**: Filter by type (All/Income/Expense)
- **Transaction Search**: Search transactions by description
- **Category Breakdown**: See spending by category with progress bars
- **Month-over-Month Comparison**: Shows percentage change from previous month

## Known Data (Test User: rizo)

- Total Income: 8 records = ~25.7M UZS
- Total Expenses: 2 records = 200 UZS
- Current Balance: ~25.7M UZS

Sample Income:
- 1234 USD = 15,425,000 UZS
- 100 CNY = 174,000 UZS (appears twice)
- 100 RUB = 100 UZS
- 100 USD = 1,250,000 UZS
- 300 USD = 3,750,000 UZS (appears twice)

Sample Expenses:
- 100 UZS
- 100 UZS

Total: 25,773,100 UZS income - 200 UZS expense = 25,772,900 UZS balance
