from django.apps import AppConfig
from tapir.mail.registries import mail_segment_providers, MailSegment


class CoopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.coop"

    def ready(self):
        mail_segment_providers.add(self.provide_coop_mail_segments)

    @staticmethod
    def provide_coop_mail_segments():
        from tapir.wirgarten.models import Member
        from tapir.wirgarten.tapirmail import Segments, SegmentGroups
        from tapir.core.services.active_member_provider import ActiveMemberProvider
        from tapir.wirgarten.utils import get_now, legal_status_is_cooperative

        def get_active_members():
            cache = {}
            return ActiveMemberProvider.get_active_members(
                reference_datetime=get_now(cache=cache), cache=cache
            )

        segment_registry = {
            Segments.ALL_USERS: MailSegment(
                get_queryset=get_active_members,
                label=Segments.ALL_USERS,
                group=SegmentGroups.GENERAL,
                description="Alle aktiven Mitglieder: mit mindenstens ein aus Geno-Anteilen, Vereinsmitgliedschaft, Solidarbeitrag oder laufendem bzw. zukünftigem Vertrag.",
            ),
        }

        if not legal_status_is_cooperative(cache={}):
            return segment_registry

        segment_registry |= {
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

        return segment_registry
