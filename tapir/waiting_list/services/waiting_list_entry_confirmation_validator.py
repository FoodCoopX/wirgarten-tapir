import uuid

from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404

from tapir.associations.models import AssociationMembershipType
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import WaitingListEntry
from tapir.wirgarten.utils import (
    legal_status_is_cooperative,
    legal_status_is_association,
)


class WaitingListEntryConfirmationValidator:
    @classmethod
    def validate_request_and_get_waiting_list_entry(
        cls, validated_data: dict, cache: dict
    ):
        waiting_list_entry = cls.get_entry_by_id_and_validate_link_key(
            entry_id=validated_data["entry_id"], link_key=validated_data["link_key"]
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

        if legal_status_is_cooperative(cache=cache):
            cls.validate_number_of_shares(
                order=order,
                desired_number_of_coop_shares=validated_data["number_of_coop_shares"],
                cache=cache,
            )

        if legal_status_is_association(cache=cache):
            cls.validate_association_content(
                association_membership_type_id=validated_data.get(
                    "association_membership_type_id", None
                )
            )

    @classmethod
    def validate_association_content(cls, association_membership_type_id: str | None):
        if association_membership_type_id is None:
            raise ValidationError("Keine Vereinsmitgliedschaft ausgewählt")

        membership_type = AssociationMembershipType.objects.filter(
            id=association_membership_type_id
        ).first()
        if not membership_type:
            raise ValidationError(
                f"Unbekannte Vereinsmitgliedschafttyp-ID: {association_membership_type_id}"
            )

    @classmethod
    def validate_number_of_shares(
        cls, order: TapirOrder, desired_number_of_coop_shares: int, cache: dict
    ):
        min_number_of_shares = (
            MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_tapir_order(
                order=order, cache=cache
            )
        )
        if desired_number_of_coop_shares < min_number_of_shares:
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
