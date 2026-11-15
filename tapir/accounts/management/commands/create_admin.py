import os

from django.core.management import BaseCommand
from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager


class Command(BaseCommand):
    help = "Create the initial admin account"

    def handle(self, *args, **options):
        first_name = options["first_name"] or os.environ.get(
            "TAPIR_ADMIN_FIRST_NAME", "Admin"
        )
        last_name = options["last_name"] or os.environ.get(
            "TAPIR_ADMIN_LAST_NAME", "Tapir"
        )
        email = options["email"] or os.environ.get(
            "TAPIR_ADMIN_EMAIL", "admin@example.com"
        )
        password = options["password"] or os.environ.get(
            "TAPIR_ADMIN_PASSWORD", "admin"
        )

        if TapirUser.objects.filter(email__iexact=email).exists():
            self.stdout.write(f"Admin account for {email} already exists, skipping")
            return

        with transaction.atomic():
            admin = TapirUser.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=email,
                is_staff=True,
                is_superuser=True,
            )
            KeycloakUserManager.create_keycloak_user_if_necessary(
                user=admin, initial_password=password
            )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created admin account for {email}")
        )

    def add_arguments(self, parser):
        parser.add_argument(
            "--first-name",
            help="First name (env: TAPIR_ADMIN_FIRST_NAME, default: Admin)",
            type=str,
        )
        parser.add_argument(
            "--last-name",
            help="Last name (env: TAPIR_ADMIN_LAST_NAME, default: Tapir)",
            type=str,
        )
        parser.add_argument(
            "--email",
            help=("Email address (env: TAPIR_ADMIN_EMAIL, default: admin@example.com)"),
            type=str,
        )
        parser.add_argument(
            "--password",
            help="Initial password (env: TAPIR_ADMIN_PASSWORD, default: admin)",
            type=str,
        )
