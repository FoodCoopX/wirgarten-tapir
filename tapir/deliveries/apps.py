from django.apps import AppConfig
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger


class DeliveriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.deliveries"
    MAIL_TRIGGER_JOKER_USED = "deliveries.joker_used"
    MAIL_TRIGGER_JOKER_CANCELLED = "deliveries.joker_cancelled"
    MAIL_TRIGGER_DONATION_USED = "deliveries.donation_used"
    MAIL_TRIGGER_DONATION_CANCELLED = "deliveries.donation_cancelled"

    def ready(self):
        TransactionalTrigger.register_action(
            "Joker: Joker eingesetzt",
            self.MAIL_TRIGGER_JOKER_USED,
            {"Joker Datum": "joker_date"},
        )

        TransactionalTrigger.register_action(
            "Joker: Joker storniert",
            self.MAIL_TRIGGER_JOKER_CANCELLED,
            {"Joker Datum": "joker_date"},
        )

        TransactionalTrigger.register_action(
            "Lieferung Spende: Spende eingesetzt",
            self.MAIL_TRIGGER_DONATION_USED,
            {"Spende Datum": "donation_date"},
        )

        TransactionalTrigger.register_action(
            "Lieferung Spende: Spende storniert",
            self.MAIL_TRIGGER_DONATION_CANCELLED,
            {"Spende Datum": "donation_date"},
        )
