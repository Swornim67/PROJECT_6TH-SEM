from django.contrib import admin

from .forms import AdminLoginForm
from .models import Account, Budget, Category, Expense, Income, Payee, RecurringTransaction, Tag


class VerifiedAdminSite(admin.AdminSite):
    """Django admin guarded by a second, admin-specific credential."""

    login_form = AdminLoginForm

    def has_permission(self, request):
        if not super().has_permission(request):
            return False
        try:
            return request.user.admin_verification.is_verified
        except AttributeError:
            return False


verified_admin_site = VerifiedAdminSite(name="admin")


@admin.register(Income, site=verified_admin_site)
class IncomeAdmin(admin.ModelAdmin):
    """Make income records manageable directly from the Django admin list."""

    list_display = ("date", "user", "category", "amount", "currency", "description")
    list_editable = ("category", "amount", "currency", "description")
    list_filter = ("currency", "category", "date")
    search_fields = ("description", "user__username", "category__name")
    list_select_related = ("user", "category")
    ordering = ("-date", "-created_at")


verified_admin_site.register([Account, Category, Expense, Budget, Payee, Tag, RecurringTransaction])
