from django.core.management.base import BaseCommand

from tapir.utils.management.commands.populate_functions import (
    populate_users,
    clear_data,
    reset_all_test_data,
)


class Command(BaseCommand):
    help = "A list of helper function to fill the database with test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users", help="Create 500 randomised users", action="store_true"
        )
        parser.add_argument(
            "--clear",
            help="Clears most objects (except admins)",
            action="store_true",
        )
        parser.add_argument(
            "--reset_all",
            help="Runs --clear then populate most models",
            action="store_true",
        )

    def handle(self, *args, **options):
        if options["users"]:
            populate_users()
        if options["clear"]:
            clear_data()
        if options["reset_all"]:
            reset_all_test_data()
