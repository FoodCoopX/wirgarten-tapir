import sys

from django.core.management import BaseCommand

from tapir.accounts.models import TapirUser


class Command(BaseCommand):
    help = "Create the initial admin account"

    def handle(self, *args, **options):
        # if TapirUser.objects.filter(is_superuser=True).exists():
        #    sys.stderr.write(
        #        "There is already an admin account in the system, this command is disabled.\n"
        #    )
        #    return

        admin = TapirUser(
            first_name=options["first_name"],
            last_name=options["last_name"],
            email=options["email"],
            is_staff=True,
            is_superuser=True,
        )
        admin.save(initial_password=options["password"])

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
