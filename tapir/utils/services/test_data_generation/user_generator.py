import datetime
import json
import os
import pathlib
import random
from math import floor
from typing import Dict, List, Set

from faker import Faker
from tapir_mail.service.shortcuts import make_timezone_aware

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.solidarity_validator import SolidarityValidator
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.config import Organization
from tapir.utils.json_user import JsonUser
from tapir.utils.models import copy_user_info
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_timezone_aware_datetime, get_from_cache_or_compute
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import (
    Member,
    GrowingPeriod,
    Subscription,
    PickupLocation,
    MemberPickupLocation,
    Product,
    HarvestShareProduct,
    CoopShareTransaction,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import (
    get_or_create_mandate_ref,
)
from tapir.wirgarten.tasks import generate_member_numbers
from tapir.wirgarten.utils import get_today


class UserGenerator:
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
    def get_user_count(cls, organization: Organization):
        if organization == Organization.BIOTOP:
            return 250
        return 200

    @classmethod
    def generate_users_and_subscriptions(cls, organization: Organization):
        user_count = cls.get_user_count(organization)
        # Users generated with https://randomuser.me
        print(f"Creating {user_count} users, this may take a while")
        random.seed("wirgarten")

        fake = Faker()

        parsed_users = cls.get_test_users()

        cache = {}
        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)

        products_from_base_type = HarvestShareProduct.objects.filter(
            type=base_product_type
        ).select_related("type")
        products_from_base_type = [product for product in products_from_base_type]
        additional_products = (
            Product.objects.exclude(type=base_product_type)
            .exclude(type__must_be_subscribed_to=True)
            .select_related("type")
        )
        additional_products = [product for product in additional_products]
        required_products = [
            product
            for product in Product.objects.filter(type__must_be_subscribed_to=True)
        ]

        members_that_need_a_pickup_location = set()

        for index, parsed_user in enumerate(parsed_users[:user_count]):
            if (index + 1) % 20 == 0:
                print(f"\t{index+1}/{user_count}...")
            cls.generate_user(
                parsed_user=parsed_user,
                cache=cache,
                fake=fake,
                products_from_base_type=products_from_base_type,
                additional_products=additional_products,
                members_that_need_a_pickup_location=members_that_need_a_pickup_location,
                required_products=required_products,
            )
            CoopShareTransaction.objects.filter(
                valid_at__lte=get_today(cache=cache) - datetime.timedelta(days=60)
            ).update(admin_confirmed=get_today(cache=cache))

        cls.link_members_to_pickup_location(
            members_that_need_a_pickup_location, organization=organization
        )
        generate_member_numbers(print_results=False)

    @classmethod
    def generate_user(
        cls,
        parsed_user,
        cache,
        fake,
        products_from_base_type,
        additional_products,
        members_that_need_a_pickup_location,
        required_products,
    ):
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

        member_without_subscriptions = random.random() < 0.20
        min_coop_shares = 0
        if not member_without_subscriptions:
            min_coop_shares, needs_pickup_location = cls.create_subscriptions_for_user(
                member,
                create_subs_for_additional_products=False,
                cache=cache,
                products_from_base_type=products_from_base_type,
                additional_products=additional_products,
            )
            if len(additional_products) > 0 and (
                min_coop_shares > 0
                or get_parameter_value(
                    ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
                    cache=cache,
                )
            ):
                _, needs_pickup_location_additional_products = (
                    cls.create_subscriptions_for_user(
                        member,
                        create_subs_for_additional_products=True,
                        cache=cache,
                        products_from_base_type=products_from_base_type,
                        additional_products=additional_products,
                    )
                )
                needs_pickup_location = (
                    needs_pickup_location or needs_pickup_location_additional_products
                )
            if needs_pickup_location:
                members_that_need_a_pickup_location.add(member)
            if len(required_products) > 0:
                cls.create_subscription_to_required_products(
                    member=member, products=required_products, cache=cache
                )

        cls.create_coop_shares_for_user(member, min_coop_shares, cache)

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
        start_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=cls.get_random_date_in_range_biased_towards_lower_end(
                member.date_joined.date(), future_growing_period.end_date
            ),
            cache=cache,
        )
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=start_date, cache=cache
        )
        end_date = growing_period.end_date

        choices = [1, 2]
        weights = [100, 1]
        if create_subs_for_additional_products:
            choices = [0, 1, 2]
            weights = [50, 50, 1]
        number_product_subscriptions = random.choices(
            population=choices, weights=weights, k=1
        )[0]
        already_subscribed_products_ids = set()

        previous_growing_period = cls.get_past_growing_period(cache=cache)
        current_growing_period = TapirCache.get_growing_period_at_date(
            reference_date=get_today(cache=cache), cache=cache
        )

        min_shares = 0
        needs_pickup_location = False
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

            solidarity_price_percentage = random.choice(
                list(
                    SolidarityValidator.get_solidarity_dropdown_values(
                        cache=cache
                    ).keys()
                )
            )
            solidarity_price_absolute = None
            if solidarity_price_percentage == "custom":
                solidarity_price_percentage = 0
                solidarity_price_absolute = random.randrange(-25, 25)

            quantity = random.choices([1, 2, 3], weights=[100, 1, 1], k=1)[0]
            if product.type.single_subscription_only:
                quantity = 1

            if not create_subs_for_additional_products:
                min_shares += quantity * product.min_coop_shares

            if solidarity_price_percentage is not None:
                solidarity_price_percentage /= 100

            subscription = Subscription.objects.create(
                member=member,
                product=product,
                period=growing_period,
                quantity=quantity,
                start_date=start_date,
                end_date=end_date,
                solidarity_price_percentage=solidarity_price_percentage,
                solidarity_price_absolute=solidarity_price_absolute,
                mandate_ref=mandate_ref,
                admin_confirmed=cls.get_confirmation_datetime(start_date, cache=cache),
            )

            needs_pickup_location = (
                needs_pickup_location or product.type.delivery_cycle != NO_DELIVERY
            )

            if growing_period != previous_growing_period:
                continue

            subscription_got_cancelled = random.random() < 0.25
            if subscription_got_cancelled:
                days_range = (subscription.end_date - subscription.start_date).days
                subscription.cancellation_ts = make_timezone_aware(
                    datetime.datetime.combine(
                        subscription.start_date
                        + datetime.timedelta(days=random.randint(0, days_range)),
                        datetime.time(hour=12),
                    )
                )
                if TrialPeriodManager.is_product_in_trial(
                    product=subscription.product,
                    member=member,
                    cache=cache,
                    reference_date=subscription.cancellation_ts.date(),
                ):
                    subscription.end_date = (
                        TrialPeriodManager.get_earliest_trial_cancellation_date(
                            subscription,
                            reference_date=subscription.cancellation_ts.date(),
                            cache=cache,
                        )
                    )
                subscription.cancellation_admin_confirmed = (
                    cls.get_confirmation_datetime(
                        subscription.cancellation_ts.date(), cache=cache
                    )
                )
                subscription.save()
            else:
                Subscription.objects.create(
                    member=member,
                    product=product,
                    period=current_growing_period,
                    quantity=quantity,
                    start_date=current_growing_period.start_date,
                    end_date=current_growing_period.end_date,
                    solidarity_price_percentage=solidarity_price_percentage,
                    solidarity_price_absolute=solidarity_price_absolute,
                    mandate_ref=mandate_ref,
                    admin_confirmed=cls.get_confirmation_datetime(
                        start_date, cache=cache
                    ),
                )

        return min_shares, needs_pickup_location

    @classmethod
    def create_subscription_to_required_products(
        cls, member: Member, products: List[Product], cache: Dict
    ):
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=get_today(cache=cache), cache=cache
        )

        Subscription.objects.create(
            member=member,
            product=random.choice(products),
            start_date=growing_period.start_date,
            end_date=None,
            period=None,
            quantity=1,
            mandate_ref=get_or_create_mandate_ref(member, cache=cache),
            admin_confirmed=cls.get_confirmation_datetime(
                growing_period.start_date, cache=cache
            ),
        )

    @classmethod
    def create_coop_shares_for_user(cls, member: Member, min_shares: int, cache: Dict):
        shares = min_shares
        if random.random() < 0.5:
            shares += random.randint(0, 10)

        shares = max(1, min_shares)

        CoopSharePurchaseHandler.buy_cooperative_shares(
            quantity=shares,
            member=member,
            shares_valid_at=member.date_joined.date(),
            cache=cache,
        )

    @classmethod
    def link_members_to_pickup_location(
        cls,
        members_that_need_a_pickup_location: Set[Member],
        organization: Organization,
    ):
        names_of_locations_that_must_be_full = []
        if organization == Organization.BIOTOP:
            names_of_locations_that_must_be_full = [
                "Grünes Warenhaus",
                "Biotop-Hofpunkt",
                "Hochalmstraße Lenggries",
            ]
        locations_that_must_be_full = list(
            PickupLocation.objects.filter(name__in=names_of_locations_that_must_be_full)
        )
        locations_that_should_not_be_full = list(
            PickupLocation.objects.exclude(
                name__in=names_of_locations_that_must_be_full
            )
        )

        member_pickup_locations = []
        for index, member in enumerate(members_that_need_a_pickup_location):
            if floor(index / 50) >= len(locations_that_must_be_full):
                pickup_location = random.choice(locations_that_should_not_be_full)
            else:
                pickup_location = random.choice(locations_that_must_be_full)
            member_pickup_locations.append(
                MemberPickupLocation(
                    member=member,
                    pickup_location=pickup_location,
                    valid_from=member.date_joined.date(),
                )
            )

        MemberPickupLocation.objects.bulk_create(member_pickup_locations)

    @classmethod
    def get_confirmation_datetime(cls, reference_date: datetime.date, cache: dict):
        confirmation_date = reference_date + datetime.timedelta(days=1)
        confirmation_datetime = datetime.datetime.combine(
            confirmation_date, datetime.time()
        )
        confirmation_datetime = make_timezone_aware(confirmation_datetime)
        if confirmation_date <= get_today(cache=cache):
            return confirmation_datetime
        return None
