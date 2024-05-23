import logging
from dataclasses import dataclass

from dateutil.relativedelta import relativedelta
from django.db import models, transaction
from django.utils import timezone
from tapir_mail.models import (
    EmailConfigurationDispatch,
    EmailConfigurationVersion,
    ReleaseStatus,
)
from tapir_mail.service.segment import resolve_segments
from tapir_mail.service.triggers import Trigger

from tapir.wirgarten.models import Member, Subscription
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.utils import get_now

LOG = logging.getLogger(__name__)


@dataclass
class OnboardingTriggerData:
    days_offset: int
    delivery_number: int


class OnboardingTrigger(Trigger[OnboardingTriggerData]):
    @classmethod
    def get_id(cls) -> str:
        return f"{__name__}.onboarding_trigger"

    @classmethod
    def get_display_name(cls) -> str:
        return "Onboarding"

    @classmethod
    @transaction.atomic
    def _on_create(
            cls,
            email_configuration_version: EmailConfigurationVersion,
            trigger_data: OnboardingTriggerData,
    ):
        for recipient in resolve_segments(**email_configuration_version.segment_data):
            cls._delete_unsent_config_dispatch(
                version=email_configuration_version, recipient=recipient
            )
            if not hasattr(recipient, "subscription_set"):
                LOG.warning(
                    f"Recipient can't receive trigger because of a missing attribute."
                    f"\n\tRecipient: {recipient}"
                    f"\n\tTrigger: {cls}"
                    f"\n\tAttribute: subscription_set"
                )
                continue

            cls._create_new_config_dispatch(
                version=email_configuration_version,
                recipient=recipient,
                trigger_data=trigger_data,
            )

    @classmethod
    @transaction.atomic
    def on_subscription_updated(cls, subscription: Subscription):
        for version in EmailConfigurationVersion.objects.filter(
                status=ReleaseStatus.RELEASED
        ):
            trigger_data = next(
                (
                    trigger["trigger_field_values"]
                    for trigger in version.triggers or []
                    if trigger.get("trigger_id") == cls.get_id()
                ),
                None,
            )

            if trigger_data is None:
                LOG.warning(
                    f"Trigger data not found for trigger {cls.get_id()}, EmailConfigurationVersion#{version.id}"
                )
                continue

            cls._delete_unsent_config_dispatch(
                version=version, recipient=subscription.member
            )
            cls._create_new_config_dispatch(
                version=version,
                recipient=subscription.member,
                trigger_data=trigger_data,
            )

    @classmethod
    def _delete_unsent_config_dispatch(
            cls, version: EmailConfigurationVersion, recipient: Member
    ):
        EmailConfigurationDispatch.objects.filter(
            email_configuration_version=version,
            override_recipients=[recipient.email],
            is_sent=False,
        ).delete()

    @classmethod
    def _create_new_config_dispatch(
            cls,
            version: EmailConfigurationVersion,
            recipient: Member,
            trigger_data: OnboardingTriggerData,
    ):
        first_subscription = recipient.subscription_set.order_by("start_date").first()
        if not first_subscription:
            return

        first_delivery_date = get_next_delivery_date(first_subscription.start_date)
        weeks_offset = int(trigger_data["delivery"])
        days_offset = int(trigger_data["days_offset"])
        target_delivery_date = first_delivery_date + relativedelta(weeks=weeks_offset)

        scheduled_time = timezone.make_aware(
            target_delivery_date + relativedelta(days=days_offset, hour=12)
        )

        # don't dispatch if scheduled time is in the past
        if scheduled_time < get_now():
            return

        EmailConfigurationDispatch.objects.create(
            email_configuration_version=version,
            override_recipients=[recipient.email],
            scheduled_time=scheduled_time,
            is_sent=False,
        )

    @classmethod
    def validate_field_values_and_return_object(cls, field_values):
        return field_values

    @classmethod
    def get_field_definitions(cls):
        Choice = Trigger.DropdownFieldDefinition.Choice
        return [
            cls.FieldDefinition(
                field_name="days_offset",
                type="number",
                label="+/- Tage Versatz",
            ),
            cls.DropdownFieldDefinition(
                field_name="delivery",
                label="Nummer der Lieferung",
                choices=[
                    Choice(value=0, label="1ste Lieferung"),
                    Choice(value=1, label="2te Lieferung"),
                    Choice(value=2, label="3te Lieferung"),
                    Choice(value=3, label="4te Lieferung"),
                ],
            ),
        ]


models.signals.post_save.connect(
    receiver=lambda instance, **kwargs: OnboardingTrigger.on_subscription_updated(
        instance
    ),
    sender=Subscription,
)
