import datetime
import random

from tapir.utils.config import Organization
from tapir.utils.json_user import JsonUser
from tapir.utils.services.test_data_generation.user_generator import UserGenerator
from tapir.wirgarten.models import WaitingListEntry
from tapir.wirgarten.utils import get_now


class WaitingListGenerator:
    @classmethod
    def generate_waiting_list(cls, organization: Organization):
        user_count = UserGenerator.get_user_count(organization)
        waiting_list_count = 100

        parsed_users = UserGenerator.get_test_users()
        cache = {}

        entries = []
        for index, parsed_user in enumerate(
            parsed_users[user_count : user_count + waiting_list_count]
        ):
            json_user = JsonUser.from_parsed_user(parsed_user)
            entries.append(
                WaitingListEntry(
                    member=None,
                    first_name=json_user.first_name,
                    last_name=json_user.last_name,
                    phone=json_user.phone_number,
                    email=json_user.email,
                    street=json_user.street,
                    street_2=json_user.street_2,
                    postcode=json_user.postcode,
                    city=json_user.city,
                    country=json_user.country,
                    privacy_consent=get_now(cache=cache),
                    number_of_coop_shares=random.randint(0, 10),
                )
            )

        entries = WaitingListEntry.objects.bulk_create(entries)

        for entry in entries:
            entry.created_at = get_now(cache=cache) - datetime.timedelta(
                days=random.randint(0, 120),
                hours=random.randint(0, 24),
                minutes=random.randint(0, 59),
            )
            entry.privacy_consent = entry.created_at
            entry.desired_start_date = None
            if random.random() < 0.5:
                entry.desired_start_date = (
                    entry.created_at + datetime.timedelta(days=random.randint(0, 240))
                ).date()

        WaitingListEntry.objects.bulk_update(
            entries, ["created_at", "privacy_consent", "desired_start_date"]
        )
