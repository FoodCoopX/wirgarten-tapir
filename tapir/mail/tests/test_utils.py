import datetime
import unittest
from unittest.mock import patch

import faker

from tapir.mail.registries import MailSegmentRegistryProvider, mail_segment_providers
from tapir.mail.triggers.time_trigger import TimeTrigger


def mock_timezone_now(test: unittest.TestCase, now: datetime.datetime) -> None:
    patcher = patch("django.utils.timezone.now")
    test.mock_now = patcher.start()
    test.addCleanup(patcher.stop)
    test.mock_now.return_value = now


def build_time_trigger_dict(scheduled_time: datetime.datetime | None = None):
    return {
        "trigger_id": TimeTrigger.get_id(),
        "trigger_field_values": {
            "scheduled_time": (
                scheduled_time.isoformat()
                if scheduled_time
                else faker.Faker().date_time_this_decade().isoformat()
            ),
        },
    }


def add_mail_segment_provider(
    test: unittest.TestCase, provider: MailSegmentRegistryProvider
) -> None:
    mail_segment_providers.add(provider)
    test.addCleanup(mail_segment_providers.discard, provider)
