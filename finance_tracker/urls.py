from django.urls import include, path
from ledger.admin import verified_admin_site

urlpatterns = [path("admin/", verified_admin_site.urls), path("", include("ledger.urls"))]
