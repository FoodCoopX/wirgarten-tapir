from tapir_mail.triggers.transactional_trigger import (
    TransactionalTriggerData,
    TransactionalTrigger,
)

from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import WaitingListEntry


class WaitingListEntryConfirmationEmailSender:
    @staticmethod
    def send_confirmation_mail(
        entry: WaitingListEntry,
        existing_member_id: str | None = None,
        potential_member_info: (
            TransactionalTriggerData.RecipientOutsideOfBaseQueryset | None
        ) = None,
    ):
        if (
            existing_member_id is None
            and potential_member_info is None
            or existing_member_id is not None
            and potential_member_info is not None
        ):
            raise ValueError(
                f"Exactly one of `existing_member_id` or `future_member_info` must be provided. "
                f"existing_member_id:{existing_member_id}, future_member_info:{potential_member_info}"
            )

        contract_list = "</li><li>".join(
            [
                f"{product_wish.product.name} x {product_wish.quantity}"
                for product_wish in entry.product_wishes.all().select_related("product")
            ]
        )
        contract_list = f"<ul><li>{contract_list}</li></ul>"

        pickup_location_list = "</li><li>".join(
            [
                f"{pickup_location_wish.pickup_location.name}"
                for pickup_location_wish in entry.pickup_location_wishes.all()
                .select_related("pickup_location")
                .order_by("priority")
            ]
        )
        pickup_location_list = f"<ol><li>{pickup_location_list}</li></ol>"

        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=Events.CONFIRMATION_REGISTRATION_IN_WAITING_LIST,
                recipient_id_in_base_queryset=existing_member_id,
                recipient_outside_of_base_queryset=potential_member_info,
                token_data={
                    "contract_list": contract_list,
                    "pickup_location_list": pickup_location_list,
                    "desired_start_date": (
                        entry.desired_start_date.strftime("%d.%m.%Y")
                        if entry.desired_start_date is not None
                        else "so früh wie möglich"
                    ),
                },
            ),
        )
