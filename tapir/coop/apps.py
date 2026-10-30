from django.apps import AppConfig
from tapir_mail.registries import mail_segment_providers, MailSegment


class CoopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.coop"

    def ready(self):
        mail_segment_providers.add(self.provide_coop_mail_segments)

    @staticmethod
    def provide_coop_mail_segments():
        from tapir.wirgarten.models import Member
        from tapir.wirgarten.tapirmail import Segments, SegmentGroups
        from tapir.generic_exports.services.member_segment_provider import (
            MemberSegmentProvider,
        )

        return {
            Segments.ALL_USERS: MailSegment(
                get_queryset=MemberSegmentProvider.get_queryset_active_members,
                label=Segments.ALL_USERS,
                group=SegmentGroups.GENERAL,
                description="Alle aktiven Mitglieder: mit mindenstens ein aus Geno-Anteilen, Vereinsmitgliedschaft, Solidarbeitrag oder laufendem bzw. zukünftigem Vertrag.",
            ),
            Segments.COOP_MEMBERS: MailSegment(
                get_queryset=Member.objects.with_shares,
                label=Segments.COOP_MEMBERS,
                group=SegmentGroups.GENERAL,
                description="Mitglieder, die heute mindestens einen Genossenschaftsanteil haben.",
            ),
            Segments.NON_COOP_MEMBERS: MailSegment(
                get_queryset=Member.objects.without_shares,
                label=Segments.NON_COOP_MEMBERS,
                group=SegmentGroups.GENERAL,
                description="Mitglieder, die heute keinen Genossenschaftsanteil haben.",
            ),
        }
