from django.utils import timezone

from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetConfirmedMemberExtraEmailsForMember(TapirIntegrationTest):
    def test_getConfirmedMemberExtraEmailsForMember_default_returnsOnlyConfirmedExtrasOfTheGivenMember(
        self,
    ):
        member = MemberFactory.create()
        confirmed_1 = MemberExtraEmailFactory.create(
            member=member, email="a@example.com", confirmed_on=timezone.now()
        )
        MemberExtraEmailFactory.create(
            member=member, email="b@example.com", confirmed_on=None
        )
        confirmed_2 = MemberExtraEmailFactory.create(
            member=member, email="c@example.com", confirmed_on=timezone.now()
        )
        MemberExtraEmailFactory.create(confirmed_on=timezone.now())

        result = TapirCache.get_confirmed_member_extra_emails_for_member(
            member_id=member.id, cache={}
        )

        self.assertEqual([confirmed_1, confirmed_2], result)

    def test_getConfirmedMemberExtraEmailsForMember_memberHasNoExtra_returnsEmptyList(
        self,
    ):
        member = MemberFactory.create()

        result = TapirCache.get_confirmed_member_extra_emails_for_member(
            member_id=member.id, cache={}
        )

        self.assertEqual([], result)
