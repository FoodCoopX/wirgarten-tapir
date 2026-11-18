from django.apps import AppConfig
from tapir_mail.registries import mail_segment_providers, MailSegment


class AssociationsConfig(AppConfig):
    name = "tapir.associations"

    MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_END_DATE_SET = (
        "associations.membership_end_date_set"
    )
    MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_ENDS_TODAY = (
        "associations.membership_ends_today"
    )

    def ready(self):
        mail_segment_providers.add(self.provide_association_mail_segments)

        from tapir.wirgarten.mail_events import Events
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
            required=lambda cache: legal_status_is_association(cache=cache),
        )

        register_transactional_trigger(
            name="Verein: Beitrittsbestätigung für Vereine",
            key=Events.ASSOCIATION_MEMBERSHIP_ENTRY,
            tokens={
                "Mitgliedschaft-Typ": "membership_type_name",
                "Beitrittsdatum": "membership_start_date",
            },
            required=lambda cache: legal_status_is_association(cache=cache),
        )

        register_transactional_trigger(
            name="Verein: Vereinsmitgliedschaft endet heute",
            key=self.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_ENDS_TODAY,
            tokens={
                "Mitgliedschaft-Typ": "membership_type_name",
                "Kündigungsregistrierungsdatum": "end_date_set_on",
            },
            required=lambda cache: legal_status_is_association(cache=cache),
        )

    @staticmethod
    def provide_association_mail_segments():
        from tapir.associations.services.association_member_segment_provider import (
            AssociationMemberSegmentProvider,
        )
        from tapir.wirgarten.tapirmail import Segments, SegmentGroups
        from tapir.wirgarten.utils import legal_status_is_association

        if not legal_status_is_association(cache={}):
            return {}

        return {
            Segments.ASSOCIATION_MEMBERS: MailSegment(
                get_queryset=AssociationMemberSegmentProvider.get_queryset_with_association_membership,
                label=Segments.ASSOCIATION_MEMBERS,
                group=SegmentGroups.GENERAL,
                description="Mitglieder, die heute eine aktive Vereinsmitgliedschaft haben.",
            ),
            Segments.NON_ASSOCIATION_MEMBERS: MailSegment(
                get_queryset=AssociationMemberSegmentProvider.get_queryset_without_association_membership,
                label=Segments.NON_ASSOCIATION_MEMBERS,
                group=SegmentGroups.GENERAL,
                description="Mitglieder, die heute keine aktive Vereinsmitgliedschaft haben.",
            ),
        }
