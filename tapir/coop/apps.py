from django.apps import AppConfig
from tapir_mail.registries import mail_segment_providers


class CoopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.coop"

    def ready(self):
        mail_segment_providers.add(self.provide_coop_mail_segments)

    @staticmethod
    def provide_coop_mail_segments():
        from tapir.wirgarten.models import Member
        from tapir.wirgarten.tapirmail import Segments
        from tapir.generic_exports.services.member_segment_provider import (
            MemberSegmentProvider,
        )

        return {
            Segments.ALL_USERS: MemberSegmentProvider.get_queryset_active_members,
            Segments.COOP_MEMBERS: Member.objects.with_shares,
            Segments.NON_COOP_MEMBERS: Member.objects.without_shares,
        }
