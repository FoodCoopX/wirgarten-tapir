from django.core.management import BaseCommand

from tapir.accounts.models import TapirUser
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager


class Command(BaseCommand):
    help = "Create the initial admin account"

    def handle(self, *args, **options):
        admin = TapirUser.objects.create(
            first_name=options["first_name"],
            last_name=options["last_name"],
            email=options["email"],
            username=options["email"],
            is_staff=True,
            is_superuser=True,
        )
        KeycloakUserManager.create_keycloak_user_if_necessary(
            user=admin, initial_password=options["password"], cache={}
        )

    def add_arguments(self, parser):
        parser.add_argument(
            "--first-name",
            help="First name",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--last-name",
            help="Last name",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--email",
            help="Email address",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--password", help="Initial Password", type=str, required=True
        )
