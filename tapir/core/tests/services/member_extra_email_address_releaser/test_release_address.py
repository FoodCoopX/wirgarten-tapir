from tapir.core.services.member_extra_email_address_releaser import (
    MemberExtraEmailAddressReleaser,
)
from tapir.wirgarten.models import MemberExtraEmail, MemberExtraEmailDeletedLogEntry
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestReleaseAddress(TapirIntegrationTest):
    def test_releaseAddress_default_deletesExtrasWithTheAddressAndLogsOnTheirMember(
        self,
    ):
        released_1 = MemberExtraEmailFactory.create(email="address@example.com")
        released_2 = MemberExtraEmailFactory.create(email="address@example.com")
        kept = MemberExtraEmailFactory.create(email="other@example.com")
        actor = MemberFactory.create()

        MemberExtraEmailAddressReleaser.release_address(
            address="address@example.com", actor=actor
        )

        self.assertEqual([kept], list(MemberExtraEmail.objects.all()))
        self.assertEqual(
            {
                (released_1.member_id, "address@example.com", actor.id),
                (released_2.member_id, "address@example.com", actor.id),
            },
            set(
                MemberExtraEmailDeletedLogEntry.objects.values_list(
                    "user_id", "email", "actor_id"
                )
            ),
        )
