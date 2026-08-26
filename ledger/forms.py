from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from .models import AdminVerification, Budget, Category, Expense, Income, UserProfile, phone_number_validator

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(label="Full name", max_length=150)
    phone_number = forms.CharField(label="Phone number", max_length=16, validators=[phone_number_validator])
    class Meta:
        model = User
        fields = ("username", "first_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        if UserProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone_number

    def save(self, commit=True):
        user = super().save(commit=False); user.email = self.cleaned_data["email"]; user.first_name = self.cleaned_data["first_name"]
        if commit:
            user.save()
            UserProfile.objects.create(user=user, phone_number=self.cleaned_data["phone_number"])
        return user


class LoginForm(AuthenticationForm):
    """Apply the shared Bootstrap field styling to Django's login form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class AdminLoginForm(AuthenticationForm):
    """Require an admin-only verification code in addition to the password."""

    verification_code = forms.CharField(
        label="Admin verification code",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "one-time-code"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        super().clean()
        user = self.get_user()
        if not user:
            return self.cleaned_data
        try:
            verification = user.admin_verification
        except AdminVerification.DoesNotExist:
            verification = None
        code = self.cleaned_data.get("verification_code", "")
        if not user.is_staff or not verification or not verification.is_verified:
            raise ValidationError("Invalid administrator verification code.")
        if verification.is_locked():
            raise ValidationError("Administrator verification is temporarily locked. Try again in 15 minutes.")
        if not verification.check_verification_code(code):
            verification.register_failed_attempt()
            raise ValidationError("Invalid administrator verification code.")
        verification.register_successful_verification()
        return self.cleaned_data

class StyledForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs["class"] = "form-control"
        if "category" in self.fields: self.fields["category"].queryset = Category.objects.filter(user=user, type=self.category_type)

    def clean_currency(self):
        return self.cleaned_data["currency"].strip().upper()

class CategoryForm(StyledForm):
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, user=user, **kwargs)
    def clean(self):
        cleaned = super().clean()
        if self.user and cleaned.get("name") and cleaned.get("type") and Category.objects.filter(user=self.user, name__iexact=cleaned["name"], type=cleaned["type"]).exclude(pk=self.instance.pk).exists():
            self.add_error("name", "You already have a category with this name and type.")
        return cleaned
    class Meta: model = Category; fields = ["name", "type"]

class IncomeForm(StyledForm):
    category_type = "income"
    class Meta:
        model = Income; fields = ["category", "amount", "currency", "description", "date"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

class ExpenseForm(StyledForm):
    category_type = "expense"
    class Meta:
        model = Expense; fields = ["category", "amount", "currency", "payment_method", "description", "date"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

class BudgetForm(StyledForm):
    category_type = "expense"
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, user=user, **kwargs)
    def clean(self):
        cleaned = super().clean()
        category, month = cleaned.get("category"), cleaned.get("month")
        if self.user and category and month and Budget.objects.filter(user=self.user, category=category, month=month).exclude(pk=self.instance.pk).exists():
            self.add_error("month", "A budget for this category and month already exists.")
        return cleaned
    class Meta:
        model = Budget; fields = ["category", "month", "amount_limit"]
        widgets = {"month": forms.DateInput(attrs={"type": "date"})}


class ReportFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("start_date") and cleaned.get("end_date") and cleaned["start_date"] > cleaned["end_date"]:
            self.add_error("end_date", "The end date must be on or after the start date.")
        return cleaned
