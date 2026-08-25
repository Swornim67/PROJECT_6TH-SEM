from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .forms import LoginForm
urlpatterns = [
 path("", views.dashboard, name="dashboard"), path("register/", views.register, name="register"), path("login/", auth_views.LoginView.as_view(template_name="ledger/login.html", authentication_form=LoginForm), name="login"), path("logout/", auth_views.LogoutView.as_view(), name="logout"),
 path("categories/", views.categories, name="categories"), path("income/", views.income_list, name="income_list"), path("income/new/", views.income_create, name="income_create"), path("income/<int:pk>/edit/", views.income_edit, name="income_edit"), path("income/<int:pk>/delete/", views.income_delete, name="income_delete"),
 path("expenses/", views.expense_list, name="expense_list"), path("expenses/new/", views.expense_create, name="expense_create"), path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"), path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"), path("budgets/", views.budgets, name="budgets"), path("reports/", views.reports, name="reports"), path("reports/excel/", views.export_excel, name="export_excel"), path("reports/pdf/", views.export_pdf, name="export_pdf"),]
