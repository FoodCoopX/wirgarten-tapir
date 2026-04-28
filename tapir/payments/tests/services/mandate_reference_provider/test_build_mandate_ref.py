from unittest.mock import patch, Mock

from django.core.exceptions import ImproperlyConfigured

from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.wirgarten.parameter_keys import ParameterKeys
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
            member=member, pattern="{vorname}/{nachname}/{zufall}", cache={}
        )

        self.assertEqual("MAXIM/MUSTE/RANDOMCHARS", result)

    @patch("tapir.payments.services.mandate_reference_provider.nanoid.generate")
    def test_buildMandateRef_patternWithMemberNumberShort_substitutesMemberNumber(
        self, mock_generate: Mock
    ):
        mock_generate.return_value = "RANDOMCHARS"
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=42)

        result = MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{mitgliedsnummer_kurz}-{zufall}", cache={}
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
            member=member, pattern="{vorname}/{nachname}/{zufall}", cache={}
        )

        self.assertTrue(result.startswith("THEOP/MULLE/"))

    def test_buildMandateRef_default_resultIsUppercased(self):
        member = MemberFactory.build(first_name="john", last_name="doe", member_no=1)

        result = MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{vorname}/{nachname}", cache={}
        )

        self.assertEqual("JOHN/DOE", result)

    def test_buildMandateRef_patternHasRandom_resultLengthIs35(self):
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=42)

        result = MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{vorname}/{nachname}/{zufall}", cache={}
        )

        self.assertEqual(35, len(result))

    def test_buildMandateRef_patternRequiresMemberNumberAndMemberNumberIsNone_raisesError(
        self,
    ):
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=None)

        with self.assertRaises(ImproperlyConfigured):
            MandateReferenceProvider.build_mandate_ref(
                member=member, pattern="{mitgliedsnummer_kurz}-{zufall}", cache={}
            )

    def test_buildMandateRef_memberNumberIsNoneButPatternDoesNotRequireIt_doesNotRaise(
        self,
    ):
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=None)

        MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{vorname}/{nachname}/{zufall}", cache={}
        )

    @patch(
        "tapir.payments.services.mandate_reference_provider.MemberNumberService.format_member_number"
    )
    def test_buildMandateRef_patternWithMemberNumberLong_substitutesFormattedMemberNumber(
        self, mock_format_member_number: Mock
    ):
        mock_format_member_number.return_value = "BT0042"
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=42)
        cache = {}

        result = MandateReferenceProvider.build_mandate_ref(
            member=member, pattern="{vorname}-{mitgliedsnummer_lang}", cache=cache
        )

        self.assertEqual("JOHN-BT0042", result)
        mock_format_member_number.assert_called_once_with(member_number=42, cache=cache)

    @patch("tapir.payments.services.mandate_reference_provider.get_parameter_value")
    @patch(
        "tapir.payments.services.mandate_reference_provider.MemberNumberService.build_formatted_number"
    )
    def test_buildMandateRef_patternWithMemberNumberWithoutPrefix_substitutesFormattedNumberWithEmptyPrefix(
        self,
        mock_build_formatted_number: Mock,
        mock_get_parameter_value: Mock,
    ):
        mock_build_formatted_number.return_value = "0042"
        mock_get_parameter_value.return_value = 4
        member = MemberFactory.build(first_name="John", last_name="Doe", member_no=42)
        cache = {}

        result = MandateReferenceProvider.build_mandate_ref(
            member=member,
            pattern="{vorname}-{mitgliedsnummer_ohne_prefix}",
            cache=cache,
        )

        self.assertEqual("JOHN-0042", result)
        mock_build_formatted_number.assert_called_once_with(
            member_number=42, prefix="", length=4
        )
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, cache=cache
        )
