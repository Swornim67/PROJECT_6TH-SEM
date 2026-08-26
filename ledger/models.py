from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

phone_number_validator = RegexValidator(
    regex=r"^\+?[1-9]\d{6,14}$",
    message="Enter a valid phone number with 7 to 15 digits, optionally starting with +.",
)
currency_validator = RegexValidator(
    regex=r"^[A-Z]{3}$",
    message="Use a three-letter uppercase currency code, for example NPR.",
)


class UserProfile(models.Model):
    """Additional account details that are not available on Django's built-in user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=16, unique=True, null=True, blank=True, validators=[phone_number_validator])

    def __str__(self):
        return self.user.username


class AdminVerification(models.Model):
    """A second, private credential required for access to the admin site."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_verification",
    )
    verification_code_hash = models.CharField(max_length=128)
    is_verified = models.BooleanField(default=False)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    def set_verification_code(self, verification_code):
        self.verification_code_hash = make_password(verification_code)

    def check_verification_code(self, verification_code):
        return check_password(verification_code, self.verification_code_hash)

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def register_failed_attempt(self):
        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            self.locked_until = timezone.now() + timedelta(minutes=15)
            self.failed_attempts = 0
        self.save(update_fields=["failed_attempts", "locked_until"])

    def register_successful_verification(self):
        self.failed_attempts = 0
        self.locked_until = None
        self.last_verified_at = timezone.now()
        self.save(update_fields=["failed_attempts", "locked_until", "last_verified_at"])

    def __str__(self):
        return f"Admin verification for {self.user.username}"

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
    currency = models.CharField(max_length=3, default="NPR", validators=[currency_validator])
    description = models.TextField(blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    category_type = None

    def clean(self):
        errors = {}
        if self.category_id and self.user_id and self.category.user_id != self.user_id:
            errors["category"] = "The category must belong to your account."
        if self.category_id and self.category_type and self.category.type != self.category_type:
            errors["category"] = f"Select an {self.category_type} category for this transaction."
        if errors:
            raise ValidationError(errors)

    class Meta: abstract = True; ordering = ["-date", "-created_at"]

class Income(TransactionBase):
    category_type = Category.INCOME
    class Meta: ordering = ["-date", "-created_at"]
    def __str__(self): return f"Income: {self.amount}"

class Expense(TransactionBase):
    category_type = Category.EXPENSE
    PAYMENT_CHOICES = [("cash", "Cash"), ("card", "Card"), ("bank", "Bank transfer"), ("mobile", "Mobile wallet"), ("other", "Other")]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="cash")
    class Meta: ordering = ["-date", "-created_at"]
    def __str__(self): return f"Expense: {self.amount}"

class Budget(models.Model):
    MAX_LIMIT = Decimal("2100000.00")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, limit_choices_to={"type": "expense"})
    month = models.DateField(help_text="Use the first day of the budget month.")
    amount_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00"), message="Budget cannot be negative."),
            MaxValueValidator(MAX_LIMIT),
        ],
        help_text="Enter an amount from Rs 0 to Rs 21,00,000. Zero means no allocation.",
    )
    class Meta:
        ordering = ["-month"]
        constraints = [models.UniqueConstraint(fields=["user", "category", "month"], name="unique_monthly_budget")]
    def __str__(self): return f"{self.category} — {self.month:%b %Y}"

    def clean(self):
        errors = {}
        if self.category_id and self.user_id and self.category.user_id != self.user_id:
            errors["category"] = "The category must belong to your account."
        if self.category_id and self.category.type != Category.EXPENSE:
            errors["category"] = "Budgets can only be set for expense categories."
        if self.month and self.month.day != 1:
            errors["month"] = "Use the first day of the budget month."
        if errors:
            raise ValidationError(errors)


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
