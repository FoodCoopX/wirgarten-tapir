import sys

from django.core.management.base import BaseCommand, CommandError

from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.data_generator import DataGenerator


def valid_organization_names() -> str:
    return ", ".join(organization.name for organization in Organization)


class Command(BaseCommand):
    help = "A list of helper function to fill the database with test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            help="Clears most objects",
            action="store_true",
        )
        parser.add_argument(
            "--reset_all",
            help="Runs --clear then populate most models",
            action="store_true",
        )
        parser.add_argument(
            "--bakery",
            help="Also generate bakery data. Layers on top of the chosen organization.",
            action="store_true",
        )

        # The positional form is what the READMEs use: `populate --reset_all`
        # with no organization, and `populate --reset_all BIOTOP`.
        parser.add_argument(
            "org", help=f"One of: {valid_organization_names()}", nargs="?"
        )
        parser.add_argument(
            "--org",
            dest="org_option",
            help=f"Same as the positional argument, case-insensitive. One of: {valid_organization_names()}",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            DataGenerator.clear()
        elif options["reset_all"]:
            DataGenerator.clear()
            DataGenerator.generate_all(
                self.resolve_organization(options),
                generate_bakery_data=options["bakery"],
            )
        else:
            self.print_help("manage.py", "populate")
            sys.exit(1)

    @staticmethod
    def resolve_organization(options) -> Organization:
        name = options["org_option"] or options["org"]
        if name is None:
            return Organization.BIOTOP

        try:
            return Organization[str(name).upper()]
        except KeyError:
            raise CommandError(
                f"Unknown organization '{name}'. "
                f"Valid names: {valid_organization_names()}"
            )
