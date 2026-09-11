from django.utils import timezone

from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSetExtraRecipients(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getExtraRecipients_extraAddressesDisabled_returnsEmptyList(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False)
        member = MemberFactory.create()
        MemberExtraEmail.objects.create(
            member=member,
            email="test@example.com",
            confirmed_on=timezone.now(),
        )

        result = member.get_extra_recipients(cache={})

        self.assertEqual([], result)

    def test_getExtraRecipients_noExtraAddress_returnsEmptyList(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        member = MemberFactory.create()

        result = member.get_extra_recipients(cache={})

        self.assertEqual([], result)

    def test_getExtraRecipients_hasExtraAddress_returnsCorrectList(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        member = MemberFactory.create()
        extra_1 = MemberExtraEmail.objects.create(
            member=member,
            email="test1@example.com",
            confirmed_on=timezone.now(),
        )
        MemberExtraEmail.objects.create(
            member=member, email="test2@example.com", confirmed_on=None
        )
        extra_3 = MemberExtraEmail.objects.create(
            member=member,
            email="test3@example.com",
            confirmed_on=timezone.now(),
        )

        result = member.get_extra_recipients(cache={})
        self.assertEqual({extra_1, extra_3}, set(result))
