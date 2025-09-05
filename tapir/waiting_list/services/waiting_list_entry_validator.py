from django.core.exceptions import ValidationError

from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.subscriptions.services.required_product_types_validator import (
    RequiredProductTypesValidator,
)
from tapir.subscriptions.services.single_subscription_validator import (
    SingleSubscriptionValidator,
)
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import WaitingListEntry, Member


class WaitingListEntryValidator:
    @classmethod
    def validate_creation_of_waiting_list_entry_for_a_potential_member(
        cls, order: TapirOrder, number_of_coop_shares: int, email: str, cache: dict
    ):
        if not RequiredProductTypesValidator.does_order_contain_all_required_product_types(
            order=order
        ):
            raise ValidationError("Some required products have not been selected")

        if not SingleSubscriptionValidator.are_single_subscription_products_are_ordered_at_most_once(
            order=order, cache=cache
        ):
            raise ValidationError("Single subscription product ordered more than once")

        if (
            number_of_coop_shares
            < MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_tapir_order(
                order=order, cache=cache
            )
        ):
            raise ValidationError(
                "The given number of coop shares is less than the required minimum."
            )

        if WaitingListEntry.objects.filter(email=email).exists():
            raise ValidationError(
                "Es gibt schon einen Warteliste-Eintrag mit dieser E-Mail-Adresse"
            )
        if Member.objects.filter(email=email).exists():
            raise ValidationError(
                "Es gibt schon einen Konto mit dieser E-Mail-Adresse. Wenn du deine Verträge anpassen möchtest, nutzt die Funktionen im Mitgliederbereich."
            )

    @classmethod
    def validate_creation_of_waiting_list_entry_for_an_existing_member(
        cls, member_id: str, order: TapirOrder, cache: dict
    ):
        if WaitingListEntry.objects.filter(member_id=member_id).exists():
            raise ValidationError(
                "Es gibt schon einen Warteliste-Eintrag für dieses Mitglied."
            )

        if not SingleSubscriptionValidator.are_single_subscription_products_are_ordered_at_most_once(
            order=order, cache=cache
        ):
            raise ValidationError("Single subscription product ordered more than once")
