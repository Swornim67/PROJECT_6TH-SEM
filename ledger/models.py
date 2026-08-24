from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

class Category(models.Model):
    INCOME, EXPENSE = "income", "expense"
    TYPE_CHOICES = [(INCOME, "Income"), (EXPENSE, "Expense")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["type", "name"]
        constraints = [models.UniqueConstraint(fields=["user", "name", "type"], name="unique_user_category")]
    def __str__(self): return f"{self.name} ({self.type})"

class TransactionBase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    currency = models.CharField(max_length=3, default="NPR")
    description = models.TextField(blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True; ordering = ["-date", "-created_at"]

class Income(TransactionBase):
    class Meta: ordering = ["-date", "-created_at"]
    def __str__(self): return f"Income: {self.amount}"

class Expense(TransactionBase):
    PAYMENT_CHOICES = [("cash", "Cash"), ("card", "Card"), ("bank", "Bank transfer"), ("mobile", "Mobile wallet"), ("other", "Other")]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="cash")
    class Meta: ordering = ["-date", "-created_at"]
    def __str__(self): return f"Expense: {self.amount}"

class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, limit_choices_to={"type": "expense"})
    month = models.DateField(help_text="Use the first day of the budget month.")
    amount_limit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    class Meta:
        ordering = ["-month"]
        constraints = [models.UniqueConstraint(fields=["user", "category", "month"], name="unique_monthly_budget")]
    def __str__(self): return f"{self.category} — {self.month:%b %Y}"


class Account(models.Model):
    CASH, BANK, MOBILE, CREDIT_CARD, SAVINGS, OTHER = "cash", "bank", "mobile", "credit_card", "savings", "other"
    ACCOUNT_TYPES = [
        (CASH, "Cash"), (BANK, "Bank account"), (MOBILE, "Mobile wallet"),
        (CREDIT_CARD, "Credit card"), (SAVINGS, "Savings"), (OTHER, "Other"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accounts")
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default=BANK)
    currency = models.CharField(max_length=3, default="NPR")
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["user", "name"], name="unique_user_account")]

    def __str__(self): return self.name


class Payee(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payees")
    name = models.CharField(max_length=120)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["user", "name"], name="unique_user_payee")]

    def __str__(self): return self.name


class Tag(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["user", "name"], name="unique_user_tag")]

    def __str__(self): return self.name


class RecurringTransaction(models.Model):
    INCOME, EXPENSE = "income", "expense"
    TRANSACTION_TYPES = [(INCOME, "Income"), (EXPENSE, "Expense")]
    DAILY, WEEKLY, MONTHLY, YEARLY = "daily", "weekly", "monthly", "yearly"
    FREQUENCY_CHOICES = [(DAILY, "Daily"), (WEEKLY, "Weekly"), (MONTHLY, "Monthly"), (YEARLY, "Yearly")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recurring_transactions")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="recurring_transactions")
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_transactions")
    payee = models.ForeignKey(Payee, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_transactions")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    currency = models.CharField(max_length=3, default="NPR")
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default=MONTHLY)
    start_date = models.DateField()
    next_due_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_due_date", "description"]

    @property
    def name(self):
        return self.description or f"{self.get_transaction_type_display()} recurring transaction"

    def clean(self):
        errors = {}
        if self.category_id and self.category.user_id != self.user_id:
            errors["category"] = "The category must belong to the same user."
        if self.category_id and self.transaction_type and self.category.type != self.transaction_type:
            errors["category"] = "The category type must match the transaction type."
        if self.account_id and self.account.user_id != self.user_id:
            errors["account"] = "The account must belong to the same user."
        if self.payee_id and self.payee.user_id != self.user_id:
            errors["payee"] = "The payee must belong to the same user."
        if self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "The end date cannot be earlier than the start date."
        if errors:
            raise ValidationError(errors)

    def __str__(self): return self.name
