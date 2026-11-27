from django.utils import timezone

from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetConfirmedMemberExtraEmailWithAddress(TapirIntegrationTest):
    def test_getConfirmedMemberExtraEmailWithAddress_default_returnsTheConfirmedExtra(
        self,
    ):
        MemberExtraEmailFactory.create(email="extra@example.com", confirmed_on=None)
        confirmed = MemberExtraEmailFactory.create(
            email="extra@example.com", confirmed_on=timezone.now()
        )

        result = TapirCache.get_confirmed_member_extra_email_with_address(
            address="extra@example.com", cache={}
        )

        self.assertEqual(confirmed, result)

    def test_getConfirmedMemberExtraEmailWithAddress_onlyUnconfirmedExtra_returnsNone(
        self,
    ):
        MemberExtraEmailFactory.create(email="extra@example.com", confirmed_on=None)

        result = TapirCache.get_confirmed_member_extra_email_with_address(
            address="extra@example.com", cache={}
        )

        self.assertIsNone(result)
