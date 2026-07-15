import json

from django.core.management.base import BaseCommand

from tapir.core.services.tapir_health_status_provider import TapirHealthStatusProvider


class Command(BaseCommand):
    def handle(self, *args, **options):
        print(json.dumps(TapirHealthStatusProvider.get_health_status()))
