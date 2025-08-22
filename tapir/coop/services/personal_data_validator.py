import datetime

import phonenumbers
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db.models import Q
from localflavor.generic.validators import IBANValidator

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.models import Member, WaitingListEntry
from tapir.wirgarten.utils import get_today


class PersonalDataValidator:
    @classmethod
    def validate_personal_data_new_member(
        cls,
        email: str,
        phone_number: str,
        birthdate: datetime.date,
        iban: str,
        cache: dict,
        check_waiting_list: bool,
        payment_rhythm: str,
    ):
        # format of the data defined by tapir.subscriptions.serializers.PersonalDataSerializer
        # checking that the required fields are filled and that the email is valid is already done by the serializer class

        cls.validate_email_address_not_in_use(
            email, cache=cache, check_waiting_list=check_waiting_list
        )
        cls.validate_phone_number_is_valid(phone_number)
        cls.validate_personal_data_existing_member(
            birthdate=birthdate,
            iban=iban,
            payment_rhythm=payment_rhythm,
            cache=cache,
        )

    @classmethod
    def validate_personal_data_existing_member(
        cls, birthdate: datetime.date, iban: str, payment_rhythm: str, cache: dict
    ):
        cls.validate_birthdate(birthdate, cache=cache)
        IBANValidator(iban)

        if not MemberPaymentRhythmService.is_payment_rhythm_allowed(
            payment_rhythm, cache=cache
        ):
            raise ValidationError(
                f"Diese Zahlungsintervall {payment_rhythm} is nicht erlaubt, erlaubt sind: {MemberPaymentRhythmService.get_allowed_rhythms_choices(cache=cache)}"
            )

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
    def validate_email_address_not_in_use(
        cls, email: str, cache: dict, check_waiting_list: bool
    ):
        duplicate_email_query = Member.objects.filter(
            Q(email=email) | Q(username=email)
        )

        if duplicate_email_query.exists():
            raise ValidationError(
                "Diese E-Mail-Adresse ist schon ein anderes Mitglied zugewiesen"
            )

        kc = KeycloakUserManager.get_keycloak_client(cache=cache)
        keycloak_id = kc.get_user_id(email)
        if keycloak_id is not None:
            raise ValidationError(
                "Diese E-Mail-Adresse ist schon ein anderes Mitglied zugewiesen"
            )

        if check_waiting_list and WaitingListEntry.objects.filter(email=email).exists():
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
