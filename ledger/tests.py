from datetime import date
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import AdminVerification, Budget, Category, Expense, Income

class LedgerWorkflowTests(TestCase):
    def register(self):
        return self.client.post(reverse("register"), {"username": "alex", "first_name": "Alex", "email": "alex@example.com", "phone_number": "+9779812345678", "password1": "strong-pass-123", "password2": "strong-pass-123"})

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

    def test_user_can_add_view_edit_and_delete_income(self):
        self.register()
        user = User.objects.get(username="alex")
        category = Category.objects.get(user=user, name="Salary")

        response = self.client.post(reverse("income_create"), {
            "category": category.pk, "amount": "5000.00", "currency": "NPR",
            "description": "August salary", "date": date.today(),
        })
        self.assertRedirects(response, reverse("income_list"))
        income = Income.objects.get(user=user, description="August salary")
        self.assertContains(self.client.get(reverse("income_list")), "August salary")

        response = self.client.post(reverse("income_edit", args=[income.pk]), {
            "category": category.pk, "amount": "5500.00", "currency": "NPR",
            "description": "Updated August salary", "date": date.today(),
        })
        self.assertRedirects(response, reverse("income_list"))
        income.refresh_from_db()
        self.assertEqual(str(income.amount), "5500.00")

        response = self.client.post(reverse("income_delete", args=[income.pk]))
        self.assertRedirects(response, reverse("income_list"))
        self.assertFalse(Income.objects.filter(pk=income.pk).exists())

    def test_user_can_add_view_edit_and_delete_expense(self):
        self.register()
        user = User.objects.get(username="alex")
        category = Category.objects.get(user=user, name="Food")

        response = self.client.post(reverse("expense_create"), {
            "category": category.pk, "amount": "500.00", "currency": "NPR",
            "payment_method": "cash", "description": "Groceries", "date": date.today(),
        })
        self.assertRedirects(response, reverse("expense_list"))
        expense = Expense.objects.get(user=user, description="Groceries")
        self.assertContains(self.client.get(reverse("expense_list")), "Groceries")

        response = self.client.post(reverse("expense_edit", args=[expense.pk]), {
            "category": category.pk, "amount": "650.00", "currency": "NPR",
            "payment_method": "card", "description": "Updated groceries", "date": date.today(),
        })
        self.assertRedirects(response, reverse("expense_list"))
        expense.refresh_from_db()
        self.assertEqual(str(expense.amount), "650.00")
        self.assertEqual(expense.payment_method, "card")

        response = self.client.post(reverse("expense_delete", args=[expense.pk]))
        self.assertRedirects(response, reverse("expense_list"))
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_staff_admin_can_view_edit_and_delete_income(self):
        self.register()
        user = User.objects.get(username="alex")
        income = Income.objects.create(
            user=user,
            category=Category.objects.get(user=user, name="Salary"),
            amount="5000.00",
            currency="NPR",
            description="August salary",
            date=date.today(),
        )
        staff = User.objects.create_superuser("admin", "admin@example.com", "strong-pass-123")
        verification = AdminVerification(user=staff, is_verified=True)
        verification.set_verification_code("admin-verification-code")
        verification.save()
        response = self.client.post(reverse("admin:login"), {
            "username": "admin",
            "password": "strong-pass-123",
            "verification_code": "admin-verification-code",
            "next": reverse("admin:index"),
        })
        self.assertRedirects(response, reverse("admin:index"))

        change_url = reverse("admin:ledger_income_change", args=[income.pk])
        self.assertContains(self.client.get(reverse("admin:ledger_income_changelist")), "August salary")
        response = self.client.post(change_url, {
            "user": user.pk,
            "category": income.category.pk,
            "amount": "5500.00",
            "currency": "NPR",
            "description": "Updated August salary",
            "date": date.today(),
            "_save": "Save",
        })
        self.assertRedirects(response, reverse("admin:ledger_income_changelist"))
        income.refresh_from_db()
        self.assertEqual(str(income.amount), "5500.00")
        self.assertEqual(income.description, "Updated August salary")

        response = self.client.post(reverse("admin:ledger_income_delete", args=[income.pk]), {"post": "yes"})
        self.assertRedirects(response, reverse("admin:ledger_income_changelist"))
        self.assertFalse(Income.objects.filter(pk=income.pk).exists())

    def test_admin_requires_a_private_verification_code(self):
        staff = User.objects.create_superuser("admin", "admin@example.com", "strong-pass-123")
        verification = AdminVerification(user=staff, is_verified=True)
        verification.set_verification_code("correct-private-code")
        verification.save()

        self.assertContains(self.client.get(reverse("admin:login")), "Admin verification code")

        denied = self.client.post(reverse("admin:login"), {
            "username": "admin", "password": "strong-pass-123", "verification_code": "incorrect-code",
        })
        self.assertContains(denied, "Invalid administrator verification code.")
        self.assertFalse(denied.wsgi_request.user.is_authenticated)

        regular_user = User.objects.create_user("member", password="strong-pass-123", is_staff=True)
        self.client.force_login(regular_user)
        denied = self.client.get(reverse("admin:index"))
        self.assertRedirects(denied, reverse("admin:login") + "?next=/admin/")

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

    def test_registration_validates_unique_email_phone_and_password(self):
        self.register()
        self.client.logout()
        duplicate_email = self.client.post(reverse("register"), {"username": "sam", "first_name": "Sam", "email": "ALEX@example.com", "phone_number": "+9779812345679", "password1": "strong-pass-123", "password2": "strong-pass-123"})
        self.assertContains(duplicate_email, "email address already exists")
        duplicate_phone = self.client.post(reverse("register"), {"username": "sam", "first_name": "Sam", "email": "sam@example.com", "phone_number": "+9779812345678", "password1": "strong-pass-123", "password2": "strong-pass-123"})
        self.assertContains(duplicate_phone, "phone number already exists")
        invalid_password = self.client.post(reverse("register"), {"username": "sam", "first_name": "Sam", "email": "sam@example.com", "phone_number": "+9779812345679", "password1": "short", "password2": "short"})
        self.assertContains(invalid_password, "This password is too short")

    def test_form_and_report_date_range_validation(self):
        self.register(); user = User.objects.get(username="alex")
        income_category = Category.objects.get(user=user, name="Salary")
        invalid_income = self.client.post(reverse("income_create"), {"category": income_category.pk, "amount": "10", "currency": "1n2", "date": date.today()})
        self.assertContains(invalid_income, "three-letter uppercase currency code")
        invalid_budget = self.client.post(reverse("budgets"), {"category": Category.objects.get(user=user, name="Food").pk, "month": date.today().replace(day=2), "amount_limit": "100"})
        self.assertContains(invalid_budget, "first day of the budget month")
        invalid_report = self.client.get(reverse("reports"), {"start_date": "2026-12-01", "end_date": "2026-01-01"})
        self.assertContains(invalid_report, "end date must be on or after")
        invalid_export = self.client.get(reverse("export_excel"), {"start_date": "2026-12-01", "end_date": "2026-01-01"})
        self.assertEqual(invalid_export.status_code, 400)
