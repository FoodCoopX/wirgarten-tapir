from django.core.management import BaseCommand
from django.db import transaction

from tapir.wirgarten.parameters import ParameterDefinitions


class Command(BaseCommand):
    help = "Imports the parameter definitions for all apps. It looks for instances of 'TapirParameterDefinitionImporter' and executes its 'import_definitions()' function."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Importing parameter definitions")
        ParameterDefinitions().import_definitions(bulk_create=False)
