import datetime

from tapir.configuration.models import TapirParameter
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.wirgarten.models import MandateReference
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCreateMandateRef(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_createMandateRef_default_persistsMandateReferenceWithConfiguredPattern(
        self,
    ):
        now = mock_timezone(
            test=self, now=datetime.datetime(year=1997, month=8, day=18)
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.PAYMENT_MANDATE_REFERENCE_PATTERN
        ).update(value="{mitgliedsnummer_kurz}-test")
        member = MemberFactory.create(member_no=42)

        result = MandateReferenceProvider.create_mandate_ref(member=member, cache={})

        self.assertEqual("42-TEST", result.ref)
        self.assertEqual(member.id, result.member_id)
        self.assertEqual(1, MandateReference.objects.filter(member=member).count())
        self.assertEqual(now, result.start_ts)
