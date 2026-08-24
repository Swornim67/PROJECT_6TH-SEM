from django.contrib import admin
from .models import Account, Budget, Category, Expense, Income, Payee, RecurringTransaction, Tag
admin.site.register([Account, Category, Income, Expense, Budget, Payee, Tag, RecurringTransaction])
