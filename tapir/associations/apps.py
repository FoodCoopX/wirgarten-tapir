from django.apps import AppConfig


class AssociationsConfig(AppConfig):
    name = "tapir.associations"

    MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_END_DATE_SET = (
        "associations.membership_end_date_set"
    )
    MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_ENDS_TODAY = (
        "associations.membership_ends_today"
    )

    def ready(self):
        from tapir.wirgarten.tapirmail import register_transactional_trigger
        from tapir.wirgarten.utils import legal_status_is_association

        register_transactional_trigger(
            name="Verein: End-Datum eine Vereinsmitgliedschaft festgelegt",
            key=self.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_END_DATE_SET,
            tokens={
                "End-Datum vorher": "end_date_before",
                "End-Datum nachher": "end_date_after",
                "Mitgliedschaft-Typ": "membership_type_name",
            },
            required=lambda: legal_status_is_association(cache={}),
        )

        register_transactional_trigger(
            name="Verein: Vereinsmitgliedschaft endet heute",
            key=self.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_ENDS_TODAY,
            tokens={
                "Mitgliedschaft-Typ": "membership_type_name",
                "Kündigungsregistrierungsdatum": "end_date_set_on",
            },
            required=lambda: legal_status_is_association(cache={}),
        )
