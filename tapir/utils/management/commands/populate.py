import sys

from django.core.management.base import BaseCommand

from tapir.utils.services.test_data_generator import TestDataGenerator


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

    def handle(self, *args, **options):
        if options["clear"]:
            TestDataGenerator.clear()
        elif options["reset_all"]:
            TestDataGenerator.clear()
            TestDataGenerator.generate_all()
        else:
            self.print_help("manage.py", "populate")
            sys.exit(1)
