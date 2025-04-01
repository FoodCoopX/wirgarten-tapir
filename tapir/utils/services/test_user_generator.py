import datetime
import json
import os
import pathlib
import random

from faker import Faker

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.json_user import JsonUser
from tapir.utils.models import copy_user_info
from tapir.wirgarten.forms.subscription import SOLIDARITY_PRICES
from tapir.wirgarten.models import (
    Member,
    ProductType,
    GrowingPeriod,
    HarvestShareProduct,
    Subscription,
    PickupLocation,
    MemberPickupLocation,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.member import (
    get_or_create_mandate_ref,
    get_next_contract_start_date,
    buy_cooperative_shares,
)
from tapir.wirgarten.service.products import get_current_growing_period


class TestUserGenerator:
    USER_COUNT = 200

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
        for index, parsed_user in enumerate(parsed_users[: cls.USER_COUNT]):
            if (index + 1) % 20 == 0:
                print(f"\t{index+1}/{cls.USER_COUNT}...")

            json_user = JsonUser.from_parsed_user(parsed_user)

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
            member.save(initial_password=member.email.split("@")[0])

            min_coop_shares = cls.create_base_product_subscriptions_for_user(member)
            cls.create_coop_shares_for_user(member, min_coop_shares)
            if min_coop_shares > 0:
                cls.link_member_to_pickup_location(member)

    @classmethod
    def create_base_product_subscriptions_for_user(cls, member: Member):
        base_product_type = ProductType.objects.get(
            id=get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        )

        mandate_ref = get_or_create_mandate_ref(member)
        min_start_date = GrowingPeriod.objects.order_by("start_date").first().start_date
        min_start_date = max(min_start_date, member.date_joined.date())
        max_start_date = GrowingPeriod.objects.order_by("start_date").last().start_date
        nb_days_range = (max_start_date - min_start_date).days
        start_date = get_next_contract_start_date(
            min_start_date + datetime.timedelta(days=random.randint(0, nb_days_range))
        )
        growing_period = get_current_growing_period(start_date)
        end_date = growing_period.end_date

        number_of_base_product_subscriptions = random.choices(
            [0, 1, 2], weights=[1, 5, 1], k=1
        )[0]
        already_subscribed_products_ids = set()

        min_shares = 0
        for _ in range(number_of_base_product_subscriptions):
            product = random.choice(
                HarvestShareProduct.objects.filter(type=base_product_type).exclude(
                    id__in=already_subscribed_products_ids
                )
            )
            already_subscribed_products_ids.add(product.id)

            solidarity_price = random.choice(SOLIDARITY_PRICES)[0]
            solidarity_price_absolute = None
            if solidarity_price == "custom":
                solidarity_price = 0
                solidarity_price_absolute = random.randrange(-25, 25)

            quantity = random.randint(1, 3)
            min_shares += quantity * product.min_coop_shares

            Subscription.objects.create(
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
        return min_shares

    @classmethod
    def create_coop_shares_for_user(cls, member, min_shares):
        shares = min_shares
        if random.random() < 0.5:
            shares += random.randint(0, 10)

        shares = max(1, min_shares)

        buy_cooperative_shares(
            quantity=shares,
            member=member,
            start_date=member.date_joined.date(),
        )

    @classmethod
    def link_member_to_pickup_location(cls, member: Member):
        pickup_location = random.choice(PickupLocation.objects.all())
        MemberPickupLocation.objects.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=member.date_joined.date(),
        )
