import sys

from django.core.management.base import BaseCommand

from tapir.utils.config import Organization
from tapir.utils.services.data_generator import DataGenerator


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

        parser.add_argument("org", help="One of: VEREIN, BIOTOP, WIRGARTEN", nargs="?")

    def handle(self, *args, **options):
        if options["clear"]:
            DataGenerator.clear()
        elif options["reset_all"]:
            DataGenerator.clear()
            DataGenerator.generate_all(
                Organization[options["org"]]
                if options["org"] is not None
                else Organization.BIOTOP
            )
        else:
            self.print_help("manage.py", "populate")
            sys.exit(1)
