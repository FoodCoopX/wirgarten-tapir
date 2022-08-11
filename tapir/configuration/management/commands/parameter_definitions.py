from django.core.management import BaseCommand

from tapir.configuration.models import TapirParameterDefinitionImporter


class Command(BaseCommand):
    help = "Imports the parameter definitions for all apps. It looks for instances of 'TapirParameterDefinitionImporter' and executes its 'import_definitions()' function."

    def handle(self, *args, **kwargs):
        print("Importing parameter definitions:")

        for cls in TapirParameterDefinitionImporter.__subclasses__():
            print(" - " + cls.__module__ + "." + cls.__name__)
            cls.import_definitions(cls)
