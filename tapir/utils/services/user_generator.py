import datetime
import json
import os
import pathlib
import random
from typing import Dict, List, Set

from faker import Faker

from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.utils.json_user import JsonUser
from tapir.utils.models import copy_user_info
from tapir.utils.shortcuts import get_timezone_aware_datetime, get_from_cache_or_compute
from tapir.wirgarten.forms.subscription import SOLIDARITY_PRICES
from tapir.wirgarten.models import (
    Member,
    GrowingPeriod,
    Subscription,
    PickupLocation,
    MemberPickupLocation,
    Product,
    HarvestShareProduct,
)
from tapir.wirgarten.service.member import (
    get_or_create_mandate_ref,
    get_next_contract_start_date,
    buy_cooperative_shares,
)
from tapir.wirgarten.service.products import get_current_growing_period
from tapir.wirgarten.tasks import generate_member_numbers
from tapir.wirgarten.utils import get_today


class UserGenerator:
    USER_COUNT = 200
    past_growing_period = None
    current_growing_period = None
    future_growing_period = None

    @classmethod
    def get_past_growing_period(cls, cache: Dict):
        return get_from_cache_or_compute(
            cache,
            "past_growing_period",
            lambda: GrowingPeriod.objects.order_by("start_date").first(),
        )

    @classmethod
    def get_future_growing_period(cls, cache):
        return get_from_cache_or_compute(
            cache,
            "future_growing_period",
            lambda: GrowingPeriod.objects.order_by("start_date").last(),
        )

    @staticmethod
    def get_test_users():
        path_to_json_file = os.path.join(
            pathlib.Path(__file__).parent.absolute(), "test_users.json"
        )
        file = open(path_to_json_file, encoding="UTF-8")
        json_string = file.read()
        file.close()

        return json.loads(json_string)["results"]

    @classmethod
    def generate_users_and_subscriptions(cls):
        # Users generated with https://randomuser.me
        print(f"Creating {cls.USER_COUNT} users, this may take a while")
        random.seed("wirgarten")

        fake = Faker()

        parsed_users = cls.get_test_users()

        cache = {}
        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)

        products_from_base_type = HarvestShareProduct.objects.filter(
            type=base_product_type
        ).select_related("type")
        products_from_base_type = [product for product in products_from_base_type]
        additional_products = Product.objects.exclude(
            type=base_product_type, type__must_be_subscribed_to=True
        ).select_related("type")
        additional_products = [product for product in additional_products]
        required_products = [
            product
            for product in Product.objects.filter(type__must_be_subscribed_to=True)
        ]

        members_that_need_a_pickup_location = set()

        for index, parsed_user in enumerate(parsed_users[: cls.USER_COUNT]):
            if (index + 1) % 20 == 0:
                print(f"\t{index+1}/{cls.USER_COUNT}...")

            json_user = JsonUser.from_parsed_user(parsed_user)
            json_user.date_joined = get_timezone_aware_datetime(
                cls.get_random_date_in_range_biased_towards_lower_end(
                    cls.get_past_growing_period(cache).start_date, get_today(cache)
                ),
                datetime.time(hour=random.randint(0, 23), minute=random.randint(0, 59)),
            )

            is_superuser = json_user.get_username() == "roberto.cortes"
            member = Member(
                is_superuser=is_superuser,
                is_staff=is_superuser,
                is_active=True,
                date_joined=json_user.date_joined,
                iban=fake.iban(),
                account_owner=json_user.get_full_name(),
                sepa_consent=json_user.date_joined,
                privacy_consent=json_user.date_joined,
                withdrawal_consent=json_user.date_joined,
            )
            copy_user_info(json_user, member)
            member.save(
                initial_password=member.email.split("@")[0],
                cache=cache,
            )
            member.created_at = json_user.date_joined
            member.save(cache=cache)

            min_coop_shares = cls.create_subscriptions_for_user(
                member,
                create_subs_for_additional_products=False,
                cache=cache,
                products_from_base_type=products_from_base_type,
                additional_products=additional_products,
            )
            cls.create_coop_shares_for_user(member, min_coop_shares, cache)
            if min_coop_shares > 0:
                cls.create_subscriptions_for_user(
                    member,
                    create_subs_for_additional_products=True,
                    cache=cache,
                    products_from_base_type=products_from_base_type,
                    additional_products=additional_products,
                )
                members_that_need_a_pickup_location.add(member)
                cls.create_subscription_to_required_products(
                    member=member, products=required_products, cache=cache
                )

        cls.link_members_to_pickup_location(members_that_need_a_pickup_location)
        generate_member_numbers(print_results=False)

    @classmethod
    def get_random_date_in_range_biased_towards_lower_end(
        cls, lower_boundary: datetime.date, upper_boundary: datetime.date
    ):
        nb_days_range = (upper_boundary - lower_boundary).days
        nb_days = min([random.randint(0, nb_days_range) for _ in range(3)])
        return lower_boundary + datetime.timedelta(days=nb_days)

    @classmethod
    def create_subscriptions_for_user(
        cls,
        member: Member,
        create_subs_for_additional_products: bool,
        cache: Dict,
        products_from_base_type: List[HarvestShareProduct],
        additional_products: List[Product],
    ):
        mandate_ref = get_or_create_mandate_ref(member, cache=cache)
        future_growing_period = cls.get_future_growing_period(cache=cache)
        start_date = get_next_contract_start_date(
            cls.get_random_date_in_range_biased_towards_lower_end(
                member.date_joined.date(), future_growing_period.end_date
            )
        )
        growing_period = get_current_growing_period(start_date, cache=cache)
        end_date = growing_period.end_date

        number_product_subscriptions = random.choices(
            [0, 1, 2], weights=[1, 5, 1], k=1
        )[0]
        already_subscribed_products_ids = set()

        previous_growing_period = cls.get_past_growing_period(cache=cache)
        current_growing_period = get_current_growing_period(cache=cache)

        min_shares = 0
        for _ in range(number_product_subscriptions):
            if create_subs_for_additional_products:
                possible_products = [
                    product
                    for product in additional_products
                    if product.id not in already_subscribed_products_ids
                ]
            else:
                possible_products = [
                    product
                    for product in products_from_base_type
                    if product.id not in already_subscribed_products_ids
                ]
            product = random.choice(possible_products)
            already_subscribed_products_ids.add(product.id)

            solidarity_price = random.choice(SOLIDARITY_PRICES)[0]
            solidarity_price_absolute = None
            if solidarity_price == "custom":
                solidarity_price = 0
                solidarity_price_absolute = random.randrange(-25, 25)

            quantity = random.choices([1, 2, 3], weights=[20, 1, 1], k=1)[0]
            if product.type.single_subscription_only:
                quantity = 1

            if not create_subs_for_additional_products:
                min_shares += quantity * product.min_coop_shares

            subscription = Subscription.objects.create(
                member=member,
                product=product,
                period=growing_period,
                quantity=quantity,
                start_date=start_date,
                end_date=end_date,
                solidarity_price=solidarity_price,
                solidarity_price_absolute=solidarity_price_absolute,
                mandate_ref=mandate_ref,
            )
            if growing_period == previous_growing_period:
                if random.random() < 0.25:
                    subscription.cancellation_ts = previous_growing_period.start_date
                    subscription.save()
                else:
                    Subscription.objects.create(
                        member=member,
                        product=product,
                        period=current_growing_period,
                        quantity=quantity,
                        start_date=current_growing_period.start_date,
                        end_date=current_growing_period.end_date,
                        solidarity_price=solidarity_price,
                        solidarity_price_absolute=solidarity_price_absolute,
                        mandate_ref=mandate_ref,
                    )

        return min_shares

    @classmethod
    def create_subscription_to_required_products(
        cls, member: Member, products: List[Product], cache: Dict
    ):
        growing_period = get_current_growing_period(cache=cache)

        Subscription.objects.create(
            member=member,
            product=random.choice(products),
            start_date=growing_period.start_date,
            end_date=None,
            period=None,
            mandate_ref=get_or_create_mandate_ref(member, cache=cache),
        )

    @classmethod
    def create_coop_shares_for_user(cls, member: Member, min_shares: int, cache: Dict):
        shares = min_shares
        if random.random() < 0.5:
            shares += random.randint(0, 10)

        shares = max(1, min_shares)

        buy_cooperative_shares(
            quantity=shares,
            member=member,
            start_date=member.date_joined.date(),
            cache=cache,
        )

    @classmethod
    def link_members_to_pickup_location(
        cls, members_that_need_a_pickup_location: Set[Member]
    ):
        pickup_locations = [location for location in PickupLocation.objects.all()]
        MemberPickupLocation.objects.bulk_create(
            [
                MemberPickupLocation(
                    member=member,
                    pickup_location=random.choice(pickup_locations),
                    valid_from=member.date_joined.date(),
                )
                for member in members_that_need_a_pickup_location
            ]
        )
