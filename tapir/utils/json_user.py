import datetime
from dataclasses import dataclass

from tapir.accounts.models import TapirUser
from tapir.utils.models import get_country_code
from tapir.utils.user_utils import UserUtils


# Helper class to deal with users generated from https://randomuser.me/


@dataclass
class JsonUser:
    first_name: str
    last_name: str
    email: str
    phone_number: str
    birthdate: datetime.date
    street: str
    street_2: str
    postcode: str
    city: str
    country: str
    date_joined: datetime.date
    preferred_language: str
    num_shares: int

    @classmethod
    def from_parsed_user(cls, parsed_json):
        first_name = parsed_json["name"]["first"]
        last_name = parsed_json["name"]["last"]
        email = parsed_json["email"]
        phone_number = parsed_json["phone"].replace("-", "")

        date_of_birth = parsed_json["dob"]["date"].replace("Z", "")
        birthdate = datetime.datetime.fromisoformat(date_of_birth).date()

        street = (
            parsed_json["location"]["street"]["name"]
            + " "
            + str(parsed_json["location"]["street"]["number"])
        )

        street_2 = ""
        postcode = str(parsed_json["location"]["postcode"])
        city = parsed_json["location"]["city"]
        country = get_country_code(parsed_json["location"]["country"])

        date_joined = parsed_json["registered"]["date"].replace("Z", "+00:00")
        date_joined = datetime.datetime.fromisoformat(date_joined)

        if parsed_json["nat"] == "DE":
            preferred_language = "de"
        else:
            preferred_language = "en"

        num_shares = max(parsed_json["location"]["street"]["number"] % 10, 1)

        return JsonUser(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            birthdate=birthdate,
            street=street,
            street_2=street_2,
            postcode=postcode,
            city=city,
            country=country,
            date_joined=date_joined,
            preferred_language=preferred_language,
            num_shares=num_shares,
        )

    def get_username(self) -> str:
        return self.first_name.lower() + "." + self.last_name.lower()

    def get_full_name(self) -> str:
        return self.first_name + " " + self.last_name

    def get_display_name(self) -> str:
        return UserUtils.build_display_name(self.first_name, self.last_name)

    def get_date_of_birth_str_for_input_field(self) -> str:
        return self.birthdate.strftime("%Y-%m-%d")

    def get_birthdate_display(self) -> str:
        return self.birthdate.strftime("%d.%m.%Y")

    def get_display_address(self) -> str:
        return UserUtils.build_display_address(
            self.street, self.street_2, self.postcode, self.city
        )

    def get_tapir_user(self) -> TapirUser:
        return TapirUser.objects.get(username=self.get_username())
