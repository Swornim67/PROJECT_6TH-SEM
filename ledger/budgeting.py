"""Monthly budgeting calculations shared by forms and views."""

from decimal import Decimal

from django.db.models import Sum

from .models import Budget, Expense, Income


def monthly_income(user, month):
    return Income.objects.filter(
        user=user, date__year=month.year, date__month=month.month
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")


def allocated_budget(user, month, exclude_budget=None):
    budgets = Budget.objects.filter(user=user, month=month)
    if exclude_budget and exclude_budget.pk:
        budgets = budgets.exclude(pk=exclude_budget.pk)
    return budgets.aggregate(total=Sum("amount_limit"))["total"] or Decimal("0.00")


def category_spending(user, category, month):
    return Expense.objects.filter(
        user=user, category=category, date__year=month.year, date__month=month.month
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")


def budget_progress(budget):
    spent = category_spending(budget.user, budget.category, budget.month)
    remaining = budget.amount_limit - spent
    percent = min(int((spent / budget.amount_limit) * 100), 100)
    if spent > budget.amount_limit:
        status = "Overspending"
    elif spent == budget.amount_limit:
        status = "Budget used"
    elif spent >= budget.amount_limit * Decimal("0.80"):
        status = "Warning: 80% used"
    else:
        status = "On track"
    return spent, remaining, percent, status


def expense_budget_alert(expense):
    month = expense.date.replace(day=1)
    budget = Budget.objects.filter(
        user=expense.user, category=expense.category, month=month
    ).first()
    if not budget:
        return None
    spent, remaining, _, status = budget_progress(budget)
    if status == "Overspending":
        return f"You have exceeded your {budget.category.name} budget by Rs. {abs(remaining):,.2f}."
    if status == "Budget used":
        return f"Your {budget.category.name} budget limit has been reached."
    if status.startswith("Warning"):
        return f"Warning: you have used {spent / budget.amount_limit * 100:.0f}% of your {budget.category.name} budget."
    return None


def exceeded_categories(user, month):
    """Return category budgets exceeded during one monthly budget period."""
    rows = []
    for budget in Budget.objects.filter(user=user, month=month).select_related("category"):
        spent, remaining, _, status = budget_progress(budget)
        if status == "Overspending":
            rows.append({
                "category": budget.category.name,
                "budget": budget.amount_limit,
                "spent": spent,
                "exceeded_by": abs(remaining),
            })
    return rows
