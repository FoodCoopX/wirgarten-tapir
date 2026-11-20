import datetime
from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.subscriptions.services.subscription_prerequisites_validator import (
    SubscriptionPrerequisitesValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(
    MemberPaymentRhythmService, "get_allowed_rhythms", return_value=[], autospec=True
)
@patch.object(MemberPaymentRhythmService, "is_payment_rhythm_allowed", autospec=True)
@patch.object(TapirCache, "get_member_payment_rhythm_object", autospec=True)
class TestSubscriptionPrerequisitesValidatorValidatePaymentRhythm(TapirUnitTest):
    def setUp(self):
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2024, month=5, day=1)
        )
        self.member = Mock()
        self.cache = Mock()

    def _validate(self, payment_rhythm: str | None):
        SubscriptionPrerequisitesValidator.validate_payment_rhythm(
            member=self.member, payment_rhythm=payment_rhythm, cache=self.cache
        )

    def test_validatePaymentRhythm_needsPaymentRhythmAndNoneProvided_raisesValidationError(
        self,
        mock_get_member_payment_rhythm_object: Mock,
        mock_is_payment_rhythm_allowed: Mock,
        mock_get_allowed_rhythms: Mock,
    ):
        mock_get_member_payment_rhythm_object.return_value = None

        with self.assertRaisesMessage(ValidationError, "Das Zahlungsintervall fehlt"):
            self._validate(payment_rhythm=None)

        mock_get_member_payment_rhythm_object.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=self.cache
        )
        mock_is_payment_rhythm_allowed.assert_not_called()
        mock_get_allowed_rhythms.assert_not_called()

    def test_validatePaymentRhythm_doesNotNeedPaymentRhythmAndNoneProvided_doesNotRaise(
        self,
        mock_get_member_payment_rhythm_object: Mock,
        mock_is_payment_rhythm_allowed: Mock,
        mock_get_allowed_rhythms: Mock,
    ):
        mock_get_member_payment_rhythm_object.return_value = Mock()

        self._validate(payment_rhythm=None)

        mock_get_member_payment_rhythm_object.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=self.cache
        )
        mock_is_payment_rhythm_allowed.assert_not_called()
        mock_get_allowed_rhythms.assert_not_called()

    def test_validatePaymentRhythm_paymentRhythmNotAllowed_raisesValidationError(
        self,
        mock_get_member_payment_rhythm_object: Mock,
        mock_is_payment_rhythm_allowed: Mock,
        mock_get_allowed_rhythms: Mock,
    ):
        mock_get_member_payment_rhythm_object.return_value = Mock()
        mock_is_payment_rhythm_allowed.return_value = False

        with self.assertRaisesMessage(
            ValidationError,
            "Dieses Zahlungsintervall test_rhythm ist nicht erlaubt, erlaubt sind: []",
        ):
            self._validate(payment_rhythm="test_rhythm")

        mock_is_payment_rhythm_allowed.assert_called_once_with(
            "test_rhythm", cache=self.cache
        )
        mock_get_allowed_rhythms.assert_called_once_with(cache=self.cache)

    def test_validatePaymentRhythm_paymentRhythmAllowed_doesNotRaise(
        self,
        mock_get_member_payment_rhythm_object: Mock,
        mock_is_payment_rhythm_allowed: Mock,
        mock_get_allowed_rhythms: Mock,
    ):
        mock_get_member_payment_rhythm_object.return_value = None
        mock_is_payment_rhythm_allowed.return_value = True

        self._validate(payment_rhythm="test_rhythm")

        mock_get_member_payment_rhythm_object.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=self.cache
        )
        mock_is_payment_rhythm_allowed.assert_called_once_with(
            "test_rhythm", cache=self.cache
        )
        mock_get_allowed_rhythms.assert_not_called()
