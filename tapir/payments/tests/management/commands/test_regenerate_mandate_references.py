from django.core.management import call_command

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import MandateReference
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MandateReferenceFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestRegenerateMandateReferences(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_handle_existingReferenceAlreadyMatchesPattern_doesNotCreateNewRef(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.PAYMENT_MANDATE_REFERENCE_PATTERN
        ).update(value="{mitgliedsnummer_kurz}-FIXED")
        member = MemberFactory.create(member_no=42)
        old_reference = MandateReferenceFactory.create(member=member, ref="42-FIXED")

        call_command("regenerate_mandate_references")

        references = MandateReference.objects.filter(member=member)
        self.assertEqual(1, references.count())
        self.assertEqual(old_reference, references.get())

    def test_handle_existingReferenceDiffersFromPattern_createsNewRef(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.PAYMENT_MANDATE_REFERENCE_PATTERN
        ).update(value="{mitgliedsnummer_kurz}-NEW")
        member = MemberFactory.create(member_no=42)
        MandateReferenceFactory.create(member=member, ref="42-OLD")

        call_command("regenerate_mandate_references")

        refs = MandateReference.objects.filter(member=member).order_by("-start_ts")
        self.assertEqual(2, refs.count())
        self.assertEqual("42-NEW", refs.first().ref)

    def test_handle_memberWithoutPriorReference_createsExactlyOneReference(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.PAYMENT_MANDATE_REFERENCE_PATTERN
        ).update(value="{zufall}")
        member = MemberFactory.create(member_no=42)
        self.assertEqual(0, MandateReference.objects.filter(member=member).count())

        call_command("regenerate_mandate_references")

        self.assertEqual(1, MandateReference.objects.filter(member=member).count())
