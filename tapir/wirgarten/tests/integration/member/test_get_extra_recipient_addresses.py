from django.utils import timezone
from icecream import ic

from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetExtraRecipientAddresses(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getExtraRecipientAddresses_extraAddressesDisabled_returnsEmptyList(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False)
        member = MemberFactory.create()
        MemberExtraEmail.objects.create(
            member=member,
            email="test@example.com",
            confirmed_on=timezone.now(),
        )

        result = member.get_extra_recipient_addresses(cache={})

        self.assertEqual([], result)

    def test_getExtraRecipientAddresses_noExtraAddress_returnsEmptyList(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        member = MemberFactory.create()

        result = member.get_extra_recipient_addresses(cache={})

        self.assertEqual([], result)

    def test_getExtraRecipientAddresses_hasExtraAddress_returnsCorrectList(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        member = MemberFactory.create()
        MemberExtraEmail.objects.create(
            member=member,
            email="test1@example.com",
            confirmed_on=timezone.now(),
        )
        MemberExtraEmail.objects.create(
            member=member, email="test2@example.com", confirmed_on=None
        )
        MemberExtraEmail.objects.create(
            member=member,
            email="test3@example.com",
            confirmed_on=timezone.now(),
        )

        result = member.get_extra_recipient_addresses(cache={})
        ic(result)
        self.assertEqual({"test1@example.com", "test3@example.com"}, set(result))
