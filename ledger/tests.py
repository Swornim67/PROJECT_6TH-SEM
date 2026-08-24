from datetime import date
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Budget, Category, Expense, Income

class LedgerWorkflowTests(TestCase):
    def register(self):
        return self.client.post(reverse("register"), {"username": "alex", "first_name": "Alex", "email": "alex@example.com", "password1": "strong-pass-123", "password2": "strong-pass-123"})

    def test_registration_creates_default_categories(self):
        response = self.register()
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(Category.objects.filter(user__username="alex", type="income").count(), 2)
        self.assertEqual(Category.objects.filter(user__username="alex", type="expense").count(), 4)

    def test_income_expense_budget_and_reports(self):
        self.register(); user = User.objects.get(username="alex")
        income_category = Category.objects.get(user=user, name="Salary"); expense_category = Category.objects.get(user=user, name="Food")
        self.assertEqual(self.client.post(reverse("income_create"), {"category": income_category.pk, "amount": "5000.00", "currency": "NPR", "description": "August salary", "date": date.today()}).status_code, 302)
        self.assertEqual(self.client.post(reverse("expense_create"), {"category": expense_category.pk, "amount": "500.00", "currency": "NPR", "payment_method": "cash", "description": "Groceries", "date": date.today()}).status_code, 302)
        self.assertEqual(self.client.post(reverse("budgets"), {"category": expense_category.pk, "month": date.today().replace(day=1), "amount_limit": "1000.00"}).status_code, 302)
        self.assertEqual(Income.objects.count(), 1); self.assertEqual(Expense.objects.count(), 1); self.assertEqual(Budget.objects.count(), 1)
        self.assertContains(self.client.get(reverse("reports")), "4500")

    def test_categories_are_scoped_to_owner_and_duplicates_are_safe(self):
        self.register(); user = User.objects.get(username="alex")
        response = self.client.post(reverse("categories"), {"name": "Food", "type": "expense"})
        self.assertEqual(response.status_code, 200); self.assertContains(response, "already have a category")
        other = User.objects.create_user("other", password="strong-pass-123")
        foreign = Category.objects.create(user=other, name="Private", type="income")
        response = self.client.post(reverse("income_create"), {"category": foreign.pk, "amount": "5", "currency": "NPR", "date": date.today()})
        self.assertEqual(response.status_code, 200); self.assertEqual(Income.objects.filter(user=user).count(), 0)

    def test_report_downloads(self):
        self.register()
        excel = self.client.get(reverse("export_excel")); pdf = self.client.get(reverse("export_pdf"))
        self.assertEqual(excel.status_code, 200); self.assertTrue(excel.content.startswith(b"PK"))
        self.assertEqual(pdf.status_code, 200); self.assertTrue(pdf.content.startswith(b"%PDF"))
