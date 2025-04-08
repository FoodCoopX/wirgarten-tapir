import datetime
import json
import os
import pathlib
import random
from typing import Dict, List, Set

from faker import Faker

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.json_user import JsonUser
from tapir.utils.models import copy_user_info
from tapir.utils.shortcuts import get_timezone_aware_datetime
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.forms.subscription import SOLIDARITY_PRICES
from tapir.wirgarten.models import (
    Member,
    ProductType,
    GrowingPeriod,
    Subscription,
    PickupLocation,
    MemberPickupLocation,
    Product,
    HarvestShareProduct,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.member import (
    get_or_create_mandate_ref,
    get_next_contract_start_date,
    buy_cooperative_shares,
)
from tapir.wirgarten.service.products import get_current_growing_period
from tapir.wirgarten.tasks import generate_member_numbers
from tapir.wirgarten.utils import get_today


class TestUserGenerator:
    USER_COUNT = 200
    past_growing_period = None
    current_growing_period = None
    future_growing_period = None

    @classmethod
    def get_past_growing_period(cls):
        if cls.past_growing_period is None:
            cls.past_growing_period = GrowingPeriod.objects.order_by(
                "start_date"
            ).first()
        return cls.past_growing_period

    @classmethod
    def get_current_growing_period(cls):
        if cls.current_growing_period is None:
            cls.current_growing_period = get_current_growing_period()
        return cls.current_growing_period

    @classmethod
    def get_future_growing_period(cls):
        if cls.future_growing_period is None:
            cls.future_growing_period = GrowingPeriod.objects.order_by(
                "start_date"
            ).last()
        return cls.future_growing_period

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

        parameter_cache = {}
        growing_period_cache = {}
        mandate_ref_cache = {}
        base_product_type = ProductType.objects.get(
            id=get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE, parameter_cache)
        )

        products_from_base_type = HarvestShareProduct.objects.filter(
            type=base_product_type
        ).select_related("type")
        products_from_base_type = [product for product in products_from_base_type]
        additional_products = Product.objects.exclude(
            type=base_product_type
        ).select_related("type")
        additional_products = [product for product in additional_products]

        members_that_need_a_pickup_location = set()

        for index, parsed_user in enumerate(parsed_users[: cls.USER_COUNT]):
            if (index + 1) % 20 == 0:
                print(f"\t{index+1}/{cls.USER_COUNT}...")

            json_user = JsonUser.from_parsed_user(parsed_user)
            json_user.date_joined = get_timezone_aware_datetime(
                cls.get_random_date_in_range_biased_towards_lower_end(
                    cls.get_past_growing_period().start_date, get_today(parameter_cache)
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
                parameter_cache=parameter_cache,
            )
            member.created_at = json_user.date_joined
            member.save(parameter_cache=parameter_cache)

            min_coop_shares = cls.create_subscriptions_for_user(
                member,
                create_subs_for_additional_products=False,
                parameter_cache=parameter_cache,
                growing_period_cache=growing_period_cache,
                products_from_base_type=products_from_base_type,
                additional_products=additional_products,
                mandate_ref_cache=mandate_ref_cache,
            )
            cls.create_coop_shares_for_user(
                member, min_coop_shares, parameter_cache, mandate_ref_cache
            )
            if min_coop_shares > 0:
                cls.create_subscriptions_for_user(
                    member,
                    create_subs_for_additional_products=True,
                    parameter_cache=parameter_cache,
                    growing_period_cache=growing_period_cache,
                    products_from_base_type=products_from_base_type,
                    additional_products=additional_products,
                    mandate_ref_cache=mandate_ref_cache,
                )
                members_that_need_a_pickup_location.add(member)

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
        parameter_cache: Dict,
        growing_period_cache: Dict,
        products_from_base_type: List[HarvestShareProduct],
        additional_products: List[Product],
        mandate_ref_cache: Dict,
    ):
        mandate_ref = get_or_create_mandate_ref(
            member, parameter_cache, mandate_ref_cache
        )
        future_growing_period = cls.get_future_growing_period()
        start_date = get_next_contract_start_date(
            cls.get_random_date_in_range_biased_towards_lower_end(
                member.date_joined.date(), future_growing_period.end_date
            )
        )
        growing_period = get_current_growing_period(start_date, growing_period_cache)
        end_date = growing_period.end_date

        number_product_subscriptions = random.choices(
            [0, 1, 2], weights=[1, 5, 1], k=1
        )[0]
        already_subscribed_products_ids = set()

        previous_growing_period = cls.get_past_growing_period()
        current_growing_period = cls.get_current_growing_period()

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

            quantity = random.randint(1, 3)
            if product.type.delivery_cycle == NO_DELIVERY[0]:
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
    def create_coop_shares_for_user(
        cls,
        member: Member,
        min_shares: int,
        parameter_cache: Dict,
        mandate_ref_cache: Dict,
    ):
        shares = min_shares
        if random.random() < 0.5:
            shares += random.randint(0, 10)

        shares = max(1, min_shares)

        buy_cooperative_shares(
            quantity=shares,
            member=member,
            start_date=member.date_joined.date(),
            parameter_cache=parameter_cache,
            mandate_ref_cache=mandate_ref_cache,
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
