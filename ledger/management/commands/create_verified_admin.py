import secrets
from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ledger.models import AdminVerification


class Command(BaseCommand):
    help = "Create or update an administrator protected by a private verification code."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("email")

    def handle(self, *args, **options):
        username, email = options["username"], options["email"]
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(username=username, defaults={"email": email})
        if not created and user.email and user.email != email:
            raise CommandError("That username already belongs to an account with a different email address.")
        password = getpass("Administrator password: ")
        if password != getpass("Password (again): "):
            raise CommandError("The passwords do not match.")
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        verification_code = secrets.token_urlsafe(24)
        verification, _ = AdminVerification.objects.get_or_create(user=user)
        verification.set_verification_code(verification_code)
        verification.is_verified = True
        verification.last_verified_at = timezone.now()
        verification.save()

        self.stdout.write(self.style.SUCCESS("Verified administrator is ready."))
        self.stdout.write("Store this private verification code now; it will not be shown again:")
        self.stdout.write(verification_code)
