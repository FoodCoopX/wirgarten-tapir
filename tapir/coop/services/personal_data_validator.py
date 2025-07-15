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
    def validate_personal_data_new_member(cls, personal_data: dict, cache: dict):
        # format of the data defined by tapir.subscriptions.serializers.PersonalDataSerializer
        # checking that the required fields are filled and that the email is valid is already done by the serializer class

        cls.validate_email_address_not_in_use(personal_data["email"])
        cls.validate_phone_number_is_valid(personal_data["phone_number"])
        cls.validate_personal_data_existing_member(
            birthdate=personal_data["birthdate"],
            iban=personal_data["iban"],
            cache=cache,
        )

    @classmethod
    def validate_personal_data_existing_member(
        cls, birthdate: datetime.date, iban: str, cache: dict
    ):
        cls.validate_birthdate(birthdate, cache=cache)
        IBANValidator(iban)

    @classmethod
    def validate_phone_number_is_valid(cls, phone_number: str):
        try:
            phone_number = phonenumbers.parse(phone_number, "DE")
            if not phonenumbers.is_possible_number(
                phone_number
            ) or not phonenumbers.is_valid_number(phone_number):
                raise ValidationError("Ungültiges Telefonnummer")
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValidationError("Ungültiges Telefonnummer")

    @classmethod
    def validate_email_address_not_in_use(cls, email: str):
        duplicate_email_query = Member.objects.filter(
            Q(email=email) | Q(username=email)
        )

        if duplicate_email_query.exists():
            raise ValidationError(
                "Diese E-Mail-Adresse ist schon ein anderes Mitglied zugewiesen"
            )

        kc = KeycloakUser.get_keycloak_client()
        keycloak_id = kc.get_user_id(email)
        if keycloak_id is not None:
            raise ValidationError(
                "Diese E-Mail-Adresse ist schon ein anderes Mitglied zugewiesen"
            )

    @classmethod
    def validate_birthdate(cls, birthdate: datetime.date, cache: dict):
        today = get_today(cache=cache)
        age = relativedelta(today, birthdate).years
        if age < 18:
            raise ValidationError(
                "Ungültiges geburtsdatum, Mitglied muss volljährig sein"
            )
        if age > 150:
            raise ValidationError("Ungültiges geburtsdatum")
