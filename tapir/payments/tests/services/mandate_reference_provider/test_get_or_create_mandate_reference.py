import datetime

from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.wirgarten.models import MandateReference
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MandateReferenceFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetOrCreateMandateReference(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getOrCreateMandateReference_memberHasNoExistingReference_createsAndReturnsNewReference(
        self,
    ):
        member = MemberFactory.create()

        result = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache={}
        )

        self.assertIsInstance(result, MandateReference)
        self.assertEqual(member.id, result.member_id)
        self.assertEqual(1, MandateReference.objects.filter(member=member).count())

    def test_getOrCreateMandateReference_memberHasExistingReference_returnsExistingReference(
        self,
    ):
        member = MemberFactory.create()
        existing_reference = MandateReferenceFactory.create(member=member)

        result = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache={}
        )

        self.assertEqual(existing_reference, result)
        self.assertEqual(1, MandateReference.objects.filter(member=member).count())

    def test_getOrCreateMandateReference_futureReferenceExists_returnsCurrentReference(
        self,
    ):
        member = MemberFactory.create()
        old_reference = MandateReferenceFactory.create(
            member=member,
            start_ts=datetime.datetime(
                year=2020, month=1, day=1, tzinfo=datetime.timezone.utc
            ),
        )
        MandateReferenceFactory.create(
            member=member,
            start_ts=datetime.datetime(
                year=2025, month=1, day=1, tzinfo=datetime.timezone.utc
            ),
        )

        result = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member,
            cache={},
            reference_datetime=datetime.datetime(
                year=2022, month=1, day=1, tzinfo=datetime.timezone.utc
            ),
        )

        self.assertEqual(old_reference, result)

    def test_getOrCreateMandateReference_allReferencesStartInTheFuture_returnsMostRecent(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2020, month=1, day=1))
        member = MemberFactory.create()
        MandateReferenceFactory.create(
            member=member,
            start_ts=datetime.datetime(
                year=2025, month=1, day=1, tzinfo=datetime.timezone.utc
            ),
        )
        future_new = MandateReferenceFactory.create(
            member=member,
            start_ts=datetime.datetime(
                year=2030, month=1, day=1, tzinfo=datetime.timezone.utc
            ),
        )

        result = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache={}
        )

        self.assertEqual(future_new, result)
