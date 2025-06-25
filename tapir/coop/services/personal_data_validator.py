import datetime

import phonenumbers
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db.models import Q
from localflavor.generic.validators import IBANValidator

from tapir.accounts.models import KeycloakUser
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today


class PersonalDataValidator:
    @classmethod
    def validate_personal_data(cls, personal_data: dict, cache: dict):
        # format of the data defined by tapir.subscriptions.serializers.PersonalDataSerializer
        # checking that the required fields are filled and that the email is valid is already done by the serializer class
        errors = {}
        if cls.is_email_already_used(personal_data["email"]):
            errors["email"] = "Email already in use"

        try:
            phone_number = phonenumbers.parse(personal_data["phone_number"], "DE")
            if not phonenumbers.is_possible_number(
                phone_number
            ) or not phonenumbers.is_valid_number(phone_number):
                errors["phone_number"] = "Invalid phone number"
        except phonenumbers.phonenumberutil.NumberParseException:
            errors["phone_number"] = "Invalid phone number"

        if not cls.is_birthdate_valid(personal_data["birthdate"], cache=cache):
            errors["birthdate"] = "Invalid birthdate"

        try:
            IBANValidator(personal_data["iban"])
        except ValidationError:
            errors["iban"] = "Invalid IBAN"

        return errors

    @classmethod
    def is_email_already_used(cls, email: str):
        duplicate_email_query = Member.objects.filter(
            Q(email=email) | Q(username=email)
        )

        if duplicate_email_query.exists():
            return True

        kc = KeycloakUser.get_keycloak_client()
        keycloak_id = kc.get_user_id(email)
        if keycloak_id is not None:
            return True

        return False

    @classmethod
    def is_birthdate_valid(cls, birthdate: datetime.date, cache: dict):
        today = get_today(cache=cache)
        age = relativedelta(today, birthdate).years
        return 18 < age < 150
