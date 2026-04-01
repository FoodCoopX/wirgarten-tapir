from django.apps import AppConfig

from tapir.deliveries.config import DELIVERY_DONATION_MODE_DISABLED
from tapir.wirgarten.parameter_keys import ParameterKeys


class DeliveriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.deliveries"
    MAIL_TRIGGER_JOKER_USED = "deliveries.joker_used"
    MAIL_TRIGGER_JOKER_CANCELLED = "deliveries.joker_cancelled"
    MAIL_TRIGGER_DONATION_USED = "deliveries.donation_used"
    MAIL_TRIGGER_DONATION_CANCELLED = "deliveries.donation_cancelled"

    def ready(self):
        from tapir.configuration.parameter import get_parameter_value
        from tapir.wirgarten.tapirmail import register_transactional_trigger

        register_transactional_trigger(
            name="Joker: Joker eingesetzt",
            key=self.MAIL_TRIGGER_JOKER_USED,
            tokens={"Joker Datum": "joker_date"},
            required=lambda: get_parameter_value(
                ParameterKeys.JOKERS_ENABLED, cache={}
            ),
        )

        register_transactional_trigger(
            name="Joker: Joker storniert",
            key=self.MAIL_TRIGGER_JOKER_CANCELLED,
            tokens={"Joker Datum": "joker_date"},
            required=lambda: get_parameter_value(
                ParameterKeys.JOKERS_ENABLED, cache={}
            ),
        )

        register_transactional_trigger(
            name="Lieferung Spende: Spende eingesetzt",
            key=self.MAIL_TRIGGER_DONATION_USED,
            tokens={"Spende Datum": "donation_date"},
            required=lambda: get_parameter_value(
                ParameterKeys.DELIVERY_DONATION_MODE, cache={}
            )
            != DELIVERY_DONATION_MODE_DISABLED,
        )

        register_transactional_trigger(
            name="Lieferung Spende: Spende storniert",
            key=self.MAIL_TRIGGER_DONATION_CANCELLED,
            tokens={"Spende Datum": "donation_date"},
            required=lambda: get_parameter_value(
                ParameterKeys.DELIVERY_DONATION_MODE, cache={}
            )
            != DELIVERY_DONATION_MODE_DISABLED,
        )
