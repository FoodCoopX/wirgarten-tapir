from django.utils import timezone

from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetMemberIdWithMainAddress(TapirIntegrationTest):
    def test_getMemberIdWithMainAddress_addressIsAMainAddress_returnsTheMemberId(
        self,
    ):
        member = MemberFactory.create(email="main@example.com")
        MemberFactory.create(email="other@example.com")

        result = TapirCache.get_member_id_with_main_address(
            address="main@example.com", cache={}
        )

        self.assertEqual(member.id, result)

    def test_getMemberIdWithMainAddress_addressIsOnlyAnExtra_returnsNone(self):
        MemberExtraEmailFactory.create(
            email="extra@example.com", confirmed_on=timezone.now()
        )

        result = TapirCache.get_member_id_with_main_address(
            address="extra@example.com", cache={}
        )

        self.assertIsNone(result)
