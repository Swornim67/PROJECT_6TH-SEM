from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Budget, Category, Expense, Income

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(label="Full name", max_length=150)
    class Meta:
        model = User
        fields = ("username", "first_name", "email", "password1", "password2")
    def save(self, commit=True):
        user = super().save(commit=False); user.email = self.cleaned_data["email"]; user.first_name = self.cleaned_data["first_name"]
        if commit: user.save()
        return user

class StyledForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs["class"] = "form-control"
        if "category" in self.fields: self.fields["category"].queryset = Category.objects.filter(user=user, type=self.category_type)

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
