from unittest.mock import patch, Mock, MagicMock

from rest_framework import serializers

from tapir.mail.serializers import SegmentDataSerializer
from tapir.wirgarten.tests.test_utils import TapirUnitTest
from tapir.wirgarten.models import Member


class SegmentDataSerializerTest(TapirUnitTest):
    @patch.object(SegmentDataSerializer, "validate_dynamic_segment_names_additive")
    @patch.object(SegmentDataSerializer, "validate_dynamic_segment_names_subtractive")
    @patch.object(SegmentDataSerializer, "validate_static_segment_ids_additive")
    @patch.object(SegmentDataSerializer, "validate_static_segment_ids_subtractive")
    @patch.object(SegmentDataSerializer, "validate_mail_category_ids_additive")
    def test_isValid_default_callsAllFieldValidationFunctions(self, *mocks):
        SegmentDataSerializer(data={}).is_valid()

        for mock in mocks:
            mock.asssert_called_once()

    @patch.object(SegmentDataSerializer, "validate_segments")
    def test_validateAddSegments_default_callsValidateSegments(
        self, mock_validate_segments: Mock
    ):
        add_segments = Mock()

        SegmentDataSerializer().validate_dynamic_segment_names_additive(add_segments)

        mock_validate_segments.assert_called_once_with(add_segments)

    @patch.object(SegmentDataSerializer, "validate_segments")
    def test_validateRemoveSegments_default_callsValidateSegments(
        self, mock_validate_segments: Mock
    ):
        add_segments = Mock()

        SegmentDataSerializer().validate_dynamic_segment_names_subtractive(add_segments)

        mock_validate_segments.assert_called_once_with(add_segments)

    @patch(
        "tapir.mail.serializers.get_mail_segments",
        autospec=True,
        return_value={"a_valid_segment": Member.objects.none},
    )
    def test_validateSegments_validSegment_returnsInput(self, _: MagicMock):
        result = SegmentDataSerializer().validate_segments(["a_valid_segment"])

        self.assertEqual(["a_valid_segment"], result)

    @patch(
        "tapir.mail.serializers.get_mail_segments",
        autospec=True,
        return_value={"a_valid_segment": Member.objects.none},
    )
    def test_validateSegments_invalidSegment_raisesError(self, _: MagicMock):
        with self.assertRaisesMessage(
            serializers.ValidationError,
            "The following segment names are not registered: ['an_invalid_segment']",
        ):
            SegmentDataSerializer().validate_segments(["an_invalid_segment"])

    @patch.object(SegmentDataSerializer, "validate_static_segments_general")
    def test_validateStaticSegments_default_callsValidateSegmentsGeneral(
        self, mock_validate_static_segments_general: Mock
    ):
        segments_additive = Mock()

        SegmentDataSerializer().validate_static_segment_ids_additive(segments_additive)

        mock_validate_static_segments_general.assert_called_once_with(segments_additive)

    @patch.object(SegmentDataSerializer, "validate_static_segments_general")
    def test_validateStaticSegmentsSubtractive_default_callsValidateSegments(
        self, mock_validate_static_segments_general: Mock
    ):
        segments_subtractive = Mock()

        SegmentDataSerializer().validate_static_segment_ids_subtractive(
            segments_subtractive
        )

        mock_validate_static_segments_general.assert_called_once_with(
            segments_subtractive
        )

    @patch("tapir.mail.models.StaticSegment.objects.values_list")
    def test_validateStaticSegments_validSegments_returnsInput(
        self, mock_values_list: Mock
    ):
        mock_values_list.return_value = ["a_valid_static_segment"]

        result = SegmentDataSerializer().validate_static_segments_general(
            ["a_valid_static_segment"]
        )

        self.assertEqual(["a_valid_static_segment"], result)

    @patch("tapir.mail.models.StaticSegment.objects.values_list")
    def test_validateStaticSegments_invalidSegments_raisesError(
        self, mock_values_list: Mock
    ):
        mock_values_list.return_value = ["a_valid_static_segment"]

        with self.assertRaises(serializers.ValidationError):
            SegmentDataSerializer().validate_static_segments_general(
                ["an_invalid_static_segment"]
            )
