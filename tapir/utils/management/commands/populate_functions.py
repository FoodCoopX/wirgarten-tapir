import json
import os
import pathlib
import random

from tapir.accounts.models import TapirUser
from tapir.log.models import LogEntry
from tapir.utils.json_user import JsonUser
from tapir.utils.models import copy_user_info
from tapir.wirgarten.models import Subscription


def get_test_users():
    path_to_json_file = os.path.join(
        pathlib.Path(__file__).parent.absolute(), "test_users.json"
    )
    file = open(path_to_json_file, encoding="UTF-8")
    json_string = file.read()
    file.close()

    return json.loads(json_string)["results"]


USER_COUNT = 400


def populate_users():
    # Users generated with https://randomuser.me
    print(f"Creating {USER_COUNT} users, this may take a while")

    parsed_users = get_test_users()
    for index, parsed_user in enumerate(parsed_users[:USER_COUNT]):
        if index % 50 == 0:
            print(str(index) + f"/{USER_COUNT}")
        json_user = JsonUser(parsed_user)
        randomizer = index + 1

        is_company = randomizer % 70 == 0
        is_investing = randomizer % 7 == 0 or is_company

        tapir_user = None
        if not is_company and not is_investing:
            tapir_user = TapirUser.objects.create(
                username=json_user.get_username(),
            )
            copy_user_info(json_user, tapir_user)
            tapir_user.is_staff = False
            tapir_user.is_active = True
            tapir_user.date_joined = json_user.date_joined
            tapir_user.password = tapir_user.username
            tapir_user.save()

    # start_date = json_user.date_joined
    # end_date = None
    # if randomizer % 40 == 0:
    #     start_date = json_user.date_joined + datetime.timedelta(weeks=100 * 52)
    # elif randomizer % 50 == 0:
    #     end_date = json_user.date_joined + datetime.timedelta(weeks=100 * 52)
    # elif randomizer % 60 == 0:
    #     end_date = datetime.date(day=18, month=8, year=2020)

    print("Created fake users")


def clear_data():
    print("Clearing data...")
    LogEntry.objects.all().delete()
    Subscription.objects.all().delete()
    TapirUser.objects.filter(is_staff=False).delete()
    print("Done")


def reset_all_test_data():
    random.seed("supercoop")
    clear_data()
    populate_users()
