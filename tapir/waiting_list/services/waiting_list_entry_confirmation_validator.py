import uuid

from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404

from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.wirgarten.models import WaitingListEntry


class WaitingListEntryConfirmationValidator:
    @classmethod
    def validate_request_and_get_waiting_list_entry(
        cls, validated_data: dict, cache: dict
    ):
        waiting_list_entry = cls.get_entry_by_id_and_validate_link_key(
            validated_data["entry_id"], validated_data["link_key"]
        )

        if waiting_list_entry.member is None:
            cls.validate_new_member_data(
                waiting_list_entry=waiting_list_entry,
                validated_data=validated_data,
                cache=cache,
            )

        if waiting_list_entry.product_wishes.exists():
            if not validated_data["sepa_allowed"]:
                raise ValidationError("SEPA-Mandat muss erlaubt sein")

            if not validated_data["contract_accepted"]:
                raise ValidationError("Vertragsgrundsätze müssen akzeptiert sein")

        return waiting_list_entry

    @classmethod
    def validate_new_member_data(
        cls, waiting_list_entry: WaitingListEntry, validated_data: dict, cache: dict
    ):
        PersonalDataValidator.validate_personal_data_new_member(
            email=waiting_list_entry.email,
            phone_number=str(waiting_list_entry.phone_number),
            iban=validated_data["iban"],
            account_owner=validated_data["account_owner"],
            payment_rhythm=validated_data["payment_rhythm"],
            cache=cache,
            check_waiting_list=False,
        )
        order = TapirOrderBuilder.build_tapir_order_from_waiting_list_entry(
            waiting_list_entry
        )

        min_number_of_shares = (
            MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_tapir_order(
                order, cache=cache
            )
        )
        if validated_data["number_of_coop_shares"] < min_number_of_shares:
            raise ValidationError(
                f"Diese Bestellung erfordert mindestens {min_number_of_shares} Genossenschaftsanteile"
            )

    @classmethod
    def get_entry_by_id_and_validate_link_key(
        cls, entry_id: str, link_key: str
    ) -> WaitingListEntry:
        waiting_list_entry = get_object_or_404(WaitingListEntry, id=entry_id)
        try:
            link_key = uuid.UUID(link_key)
        except ValueError:
            raise Http404(f"Unknown entry (id:{entry_id}, key:{link_key})")

        if waiting_list_entry.confirmation_link_key != link_key:
            raise Http404(f"Unknown entry (id:{entry_id}, key:{link_key})")

        return waiting_list_entry
