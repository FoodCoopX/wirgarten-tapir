from unittest.mock import patch, Mock

from django.core.exceptions import ImproperlyConfigured

from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildMandateRef(TapirUnitTest):
    @patch("tapir.payments.services.mandate_reference_provider.nanoid.generate")
    def test_buildMandateRef_patternWithFirstAndLastName_substitutesFirstFiveLetters(
        self, mock_generate: Mock
    ):
        mock_generate.return_value = "RANDOMCHARS"
        member = MemberFactory.build(
            first_name="Maximilian", last_name="Mustermann", member_no=1
        )

        result = MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{vorname}/{nachname}/{zufall}"
        )

        self.assertEqual("MAXIM/MUSTE/RANDOMCHARS", result)

    @patch("tapir.payments.services.mandate_reference_provider.nanoid.generate")
    def test_buildMandateRef_patternWithMemberNumberShort_substitutesMemberNumber(
        self, mock_generate: Mock
    ):
        mock_generate.return_value = "RANDOMCHARS"
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=42)

        result = MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{mitgliedsnummer_kurz}-{zufall}"
        )

        self.assertEqual("42-RANDOMCHARS", result)

    @patch("tapir.payments.services.mandate_reference_provider.nanoid.generate")
    def test_buildMandateRef_namesWithAccents_accentsAreTransliterated(
        self, mock_generate: Mock
    ):
        mock_generate.return_value = "RANDOMCHARS"
        member = MemberFactory.build(
            first_name="Théophile", last_name="Müller", member_no=1
        )

        result = MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{vorname}/{nachname}/{zufall}"
        )

        self.assertTrue(result.startswith("THEOP/MULLE/"))

    def test_buildMandateRef_default_resultIsUppercased(self):
        member = MemberFactory.build(first_name="john", last_name="doe", member_no=1)

        result = MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{vorname}/{nachname}"
        )

        self.assertEqual("JOHN/DOE", result)

    def test_buildMandateRef_patternHasRandom_resultLengthIs35(self):
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=42)

        result = MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{vorname}/{nachname}/{zufall}"
        )

        self.assertEqual(35, len(result))

    def test_buildMandateRef_memberNumberShortTokenAndMemberNumberIsNone_raisesError(
        self,
    ):
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=None)

        with self.assertRaises(ImproperlyConfigured):
            MandateReferenceProvider.build_mandate_ref(
                member=member, pattern="{mitgliedsnummer_kurz}-{zufall}"
            )

    def test_buildMandateRef_memberNumberIsNoneButPatternDoesNotRequireIt_doesNotRaise(
        self,
    ):
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=None)

        MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{vorname}/{nachname}/{zufall}"
        )
