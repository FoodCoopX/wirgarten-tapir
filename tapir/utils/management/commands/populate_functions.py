import json
import os
import pathlib
import random
from datetime import date

from dateutil.relativedelta import relativedelta

from tapir.accounts.models import TapirUser, EmailChangeRequest
from tapir.log.models import LogEntry
from tapir.utils.json_user import JsonUser
from tapir.utils.models import copy_user_info
from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.models import (
    Member,
    MemberPickupLocation,
    Product,
    ProductType,
    GrowingPeriod,
    MandateReference,
    Payment,
    CoopShareTransaction,
    QuestionaireTrafficSourceResponse,
    WaitingListEntry,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.service.delivery import get_active_pickup_locations
from tapir.wirgarten.service.member import (
    buy_cooperative_shares,
    get_or_create_mandate_ref,
    get_next_contract_start_date,
)


def get_test_users():
    path_to_json_file = os.path.join(
        pathlib.Path(__file__).parent.absolute(), "test_users.json"
    )
    file = open(path_to_json_file, encoding="UTF-8")
    json_string = file.read()
    file.close()

    return json.loads(json_string)["results"]


USER_COUNT = 50


# @transaction.atomic
def populate_users():
    # Users generated with https://randomuser.me
    print(f"Creating {USER_COUNT} users, this may take a while")
    random.seed("wirgarten")

    today = date.today()

    parsed_users = get_test_users()
    for index, parsed_user in enumerate(parsed_users[:USER_COUNT]):
        if (index + 1) % 10 == 0:
            print(str(index + 1) + f"/{USER_COUNT}")
        json_user = JsonUser(parsed_user)

        if json_user.get_username() == "roberto.cortes":
            wirgarten_user = TapirUser(is_superuser=True, is_staff=True)
            copy_user_info(json_user, wirgarten_user)
            wirgarten_user.save(initial_password=wirgarten_user.email.split("@")[0])
        else:
            pickup_locations = get_active_pickup_locations()
            wirgarten_user = Member(
                # username=json_user.get_username(),
                is_staff=False,
                is_active=True,
                date_joined=json_user.date_joined,
                is_superuser=False,
                iban="DE02100500000054540402",
                account_owner=json_user.get_full_name(),
                sepa_consent=json_user.date_joined,
                privacy_consent=json_user.date_joined,
                withdrawal_consent=json_user.date_joined,
                pickup_location=pickup_locations[
                    random.randint(0, len(pickup_locations) - 1)
                ],
            )
            copy_user_info(json_user, wirgarten_user)
            wirgarten_user.save(initial_password=wirgarten_user.email.split("@")[0])

            MemberPickupLocation.objects.create(
                member_id=wirgarten_user.id,
                pickup_location_id=pickup_locations[
                    random.randint(0, len(pickup_locations) - 1)
                ].id,
                valid_from=today,
            )

            min_shares = create_subscriptions(wirgarten_user)
            create_shareownership(wirgarten_user, min_shares)

    print("Created Wirgarten test users")


def create_shareownership(wirgarten_user, min_shares):
    shares = min_shares + random.randint(0, 3)
    buy_cooperative_shares(
        quantity=shares,
        member=wirgarten_user,
        start_date=get_next_contract_start_date() + relativedelta(months=1),
    )


def create_subscriptions(wirgarten_user):
    product_type = ProductType.objects.get(name=ProductTypes.HARVEST_SHARES)

    today = date.today()
    mandate_ref = get_or_create_mandate_ref(wirgarten_user)
    start_date = get_next_contract_start_date(today)
    growing_period = GrowingPeriod.objects.get(
        start_date__lte=start_date, end_date__gte=start_date
    )
    end_date = growing_period.end_date

    solidarity_price = 0.05
    sp_int = random.randint(0, 12)
    if sp_int == 8 or sp_int == 9:
        solidarity_price = -0.05
    if 7 >= sp_int >= 4:
        solidarity_price = 0.0
    if sp_int == 3:
        solidarity_price = 0.10
    if sp_int == 2:
        solidarity_price = 0.15
    if sp_int == 1:
        solidarity_price = 0.20
    if sp_int == 0:
        solidarity_price = 0.25

    already_subscribed = []
    number_of_hs_subs = random.randint(1, 10)
    if number_of_hs_subs > 3:
        number_of_hs_subs = 1

    min_shares = 0
    for x in range(number_of_hs_subs):
        product_int = random.randint(1, 4)
        product_name = "S"
        base_min_shares = 2
        if product_int == 2:
            product_name = "M"
            base_min_shares = 3
        if product_int == 3:
            product_name = "L"
            base_min_shares = 4
        if product_int == 4:
            product_name = "XL"
            base_min_shares = 5

        if product_name in already_subscribed:
            continue

        already_subscribed.append(product_name)

        quantity_int = random.randint(1, 2)
        min_shares += quantity_int * base_min_shares

        product = Product.objects.get(type=product_type, name=product_name)
        Subscription.objects.create(
            member=wirgarten_user,
            product=product,
            period=growing_period,
            quantity=quantity_int,
            start_date=start_date,
            end_date=end_date,
            solidarity_price=solidarity_price,
            mandate_ref=mandate_ref,
        )
    return min_shares


def clear_data():
    print("Clearing data...")
    LogEntry.objects.all().delete()
    Subscription.objects.all().delete()
    CoopShareTransaction.objects.all().delete()
    WaitingListEntry.objects.all().delete()
    QuestionaireTrafficSourceResponse.objects.all().delete()
    Payment.objects.all().delete()
    MandateReference.objects.all().delete()
    EmailChangeRequest.objects.all().delete()
    Member.objects.all().delete()
    TapirUser.objects.all().delete()
    print("Done")


def reset_all_test_data():
    clear_data()
    populate_users()
