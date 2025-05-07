import datetime
import itertools
import random
from typing import Dict

from faker import Faker

from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.utils.config import Organization
from tapir.utils.json_user import JsonUser
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.services.test_data_generation.user_generator import UserGenerator
from tapir.waiting_list.services.waiting_list_categories_service import (
    WaitingListCategoriesService,
)
from tapir.wirgarten.models import (
    WaitingListEntry,
    Member,
    PickupLocation,
    WaitingListPickupLocationWishes,
    WaitingListProductWishes,
    ProductType,
)
from tapir.wirgarten.utils import get_now, get_today


class WaitingListGenerator:
    CHANGE_MORE_COOP_SHARES = "more_coop_shares"
    CHANGE_MORE_PRODUCTS = "more_products"
    CHANGE_PICKUP_LOCATION = "pickup_location"
    POSSIBLE_CHANGES = [
        CHANGE_MORE_COOP_SHARES,
        CHANGE_MORE_PRODUCTS,
        CHANGE_PICKUP_LOCATION,
    ]

    @classmethod
    def generate_waiting_list(cls, organization: Organization):
        user_count = UserGenerator.get_user_count(organization)
        waiting_list_count = 100

        parsed_users = UserGenerator.get_test_users()
        cache = {}

        members = set(Member.objects.all())

        entries = []
        fake = Faker("la")
        for index, parsed_user in enumerate(
            parsed_users[user_count : user_count + waiting_list_count]
        ):
            entry = WaitingListEntry(
                privacy_consent=get_now(cache=cache),
                number_of_coop_shares=0,
            )

            if random.random() < 0.3:
                entry.comment = fake.paragraph(nb_sentences=3)

            categories = WaitingListCategoriesService.get_categories(cache=cache)
            if len(categories) > 0 and random.random() < 0.3:
                entry.category = random.choice(categories)

            if random.random() < 0.5:
                entry.member = random.choice(list(members))
                members.remove(entry.member)
                if len(members) == 0:
                    members = set(Member.objects.all())
            else:
                json_user = JsonUser.from_parsed_user(parsed_user)
                entry.first_name = json_user.first_name
                entry.last_name = json_user.last_name
                entry.phone_number = json_user.phone_number
                entry.email = json_user.email
                entry.street = json_user.street
                entry.street_2 = json_user.street_2
                entry.postcode = json_user.postcode
                entry.city = json_user.city
                entry.country = json_user.country

            entries.append(entry)

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

        combinations_of_possible_changes = []
        for nb_changes in range(1, len(cls.POSSIBLE_CHANGES) + 1):
            combinations_of_possible_changes.extend(
                itertools.combinations(cls.POSSIBLE_CHANGES, nb_changes)
            )

        all_pickup_locations = list(PickupLocation.objects.all())
        all_product_types = list(ProductType.objects.all())
        pickup_location_wishes = []
        product_wishes = []
        for entry in entries:
            desired_changes = random.choice(combinations_of_possible_changes)

            if cls.CHANGE_MORE_COOP_SHARES in desired_changes:
                entry.number_of_coop_shares = random.randint(1, 10)

            member_pickup_location_id = None
            if entry.member:
                member_pickup_location_id = MemberPickupLocationService.get_member_pickup_location_id_from_cache(
                    member_id=entry.member.id,
                    reference_date=get_today(cache=cache),
                    cache=cache,
                )
            if (
                cls.CHANGE_PICKUP_LOCATION in desired_changes
                or entry.member is None
                and cls.CHANGE_MORE_PRODUCTS in desired_changes
                or entry.member is not None
                and member_pickup_location_id is None
            ):
                pickup_location_wishes.extend(
                    cls.build_pickup_location_wishes(
                        all_pickup_locations=all_pickup_locations,
                        entry=entry,
                        cache=cache,
                    )
                )

            if cls.CHANGE_MORE_PRODUCTS in desired_changes:
                product_wishes.extend(
                    cls.build_product_wishes(
                        entry=entry, cache=cache, all_product_types=all_product_types
                    )
                )

        WaitingListEntry.objects.bulk_update(entries, ["number_of_coop_shares"])
        WaitingListPickupLocationWishes.objects.bulk_create(pickup_location_wishes)
        WaitingListProductWishes.objects.bulk_create(product_wishes)

    @classmethod
    def build_pickup_location_wishes(
        cls, all_pickup_locations, entry: WaitingListEntry, cache: Dict
    ):
        possible_pickup_locations = set(all_pickup_locations)
        if entry.member is not None:
            member_pickup_location_id = (
                MemberPickupLocationService.get_member_pickup_location_id_from_cache(
                    member_id=entry.member.id,
                    reference_date=get_today(cache=cache),
                    cache=cache,
                )
            )
            if member_pickup_location_id is not None:
                pickup_location = TapirCache.get_pickup_location_by_id(
                    cache=cache, pickup_location_id=member_pickup_location_id
                )
                possible_pickup_locations.remove(pickup_location)

        nb_wishes = random.randint(1, min(3, len(possible_pickup_locations)))
        pickup_location_wishes = []
        for priority in range(nb_wishes):
            pickup_location = random.choice(list(possible_pickup_locations))
            possible_pickup_locations.remove(pickup_location)
            pickup_location_wishes.append(
                WaitingListPickupLocationWishes(
                    waiting_list_entry=entry,
                    pickup_location=pickup_location,
                    priority=priority,
                )
            )

        return pickup_location_wishes

    @classmethod
    def build_product_wishes(
        cls, entry: WaitingListEntry, cache: Dict, all_product_types
    ):
        possible_product_types = set(all_product_types)
        nb_product_wishes = random.randint(1, min(3, len(possible_product_types)))
        product_wishes = []
        for _ in range(nb_product_wishes):
            product_type = random.choice(list(possible_product_types))
            possible_product_types.remove(product_type)
            possible_products = TapirCache.get_products_with_product_type(
                product_type_id=product_type.id, cache=cache
            )
            product = random.choice(list(possible_products))
            product_wishes.append(
                WaitingListProductWishes(
                    waiting_list_entry=entry, product=product, quantity=1
                )
            )
        return product_wishes
