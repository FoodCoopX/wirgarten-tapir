from unittest.mock import Mock

from tapir_mail.models import StaticSegmentRecipient

from tapir.core.services.member_mail_token_service import MemberMailTokenService
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestMemberMailTokenService(TapirUnitTest):
    def test_getPostAddress_default_returnsCorrectString(self):
        member = MemberFactory.build(
            street="aaa", street_2="bbb", postcode="12345", city="ccc"
        )

        result = MemberMailTokenService.get_post_address(recipient=member, cache=Mock())

        self.assertEqual("aaa, bbb, 12345 ccc", result)

    def test_getPostAddress_recipientIsStaticRecipient_returnsEmptyString(self):
        recipient = StaticSegmentRecipient()

        result = MemberMailTokenService.get_post_address(
            recipient=recipient, cache=Mock()
        )

        self.assertEqual("", result)
