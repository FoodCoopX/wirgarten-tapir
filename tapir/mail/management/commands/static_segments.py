from django.db import transaction
from django.conf import settings
from django.core.management.base import BaseCommand

from tapir.mail.models import StaticSegment


class Command(BaseCommand):
    help = "Creates static segments from settings.py"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        if hasattr(settings, "STATIC_SEGMENTS"):
            for segment, recipients in settings.STATIC_SEGMENTS.items():
                persisted_segment = StaticSegment.objects.filter(name=segment)[:1]
                if not persisted_segment.exists():
                    print("Creating segment: ", segment)
                    persisted_segment = StaticSegment.objects.create(name=segment)
                else:
                    persisted_segment = persisted_segment[0]

                for recipient in recipients:
                    print("Adding recipient: ", recipient)
                    persisted_segment.recipients.get_or_create(
                        email=recipient.get("email"),
                        first_name=recipient.get("first_name", "<first_name>"),
                        last_name=recipient.get("last_name", "<last_name>"),
                    )
