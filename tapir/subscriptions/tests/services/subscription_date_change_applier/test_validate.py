import datetime
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.renewal_cancellation_status_provider import (
    RenewalCancellationStatusProvider,
)
from tapir.subscriptions.services.subscription_date_change_applier import (
    SubscriptionDateChangeApplier,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import SubscriptionFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch(
    "tapir.subscriptions.services.subscription_date_change_applier.get_today",
    autospec=True,
    return_value=datetime.date(year=2025, month=11, day=10),
)
class TestValidate(TapirUnitTest):
    def setUp(self) -> None:
        super().setUp()
        self.subscription = SubscriptionFactory.build(
            period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2025, month=1, day=1)
            ),
        )

    def _validate(
        self,
        action: str,
        date: datetime.date | None = None,
        update_other_contracts: bool = False,
    ) -> None:
        SubscriptionDateChangeApplier.validate(
            subscription=self.subscription,
            action=action,
            date=date,
            update_other_contracts=update_other_contracts,
            cache={},
        )

    def test_validate_subscriptionOfPastGrowingPeriod_raisesError(
        self, mock_get_today: MagicMock
    ):
        mock_get_today.return_value = datetime.date(year=2026, month=1, day=10)

        with self.assertRaisesMessage(
            ValidationError,
            "Verträge aus vergangenen Vertragsperioden können nicht geändert werden",
        ):
            self._validate(
                action=SubscriptionDateChangeApplier.ACTION_CHANGE_END,
                date=datetime.date(year=2025, month=11, day=30),
            )

    def test_validate_updateOtherContractsWhenChangingStart_raisesError(
        self, _: MagicMock
    ):
        with self.assertRaisesMessage(
            ValidationError,
            "Weitere Verträge können nur beim Ändern des Vertragsendes angepasst werden",
        ):
            self._validate(
                action=SubscriptionDateChangeApplier.ACTION_CHANGE_START,
                date=datetime.date(year=2025, month=3, day=3),
                update_other_contracts=True,
            )

    def test_validate_dateMissing_raisesError(self, _: MagicMock):
        with self.assertRaisesMessage(ValidationError, "Bitte ein Datum angeben"):
            self._validate(action=SubscriptionDateChangeApplier.ACTION_CHANGE_END)

    def test_validate_newEndDateBeforeStartDate_raisesError(self, _: MagicMock):
        self.subscription.start_date = datetime.date(year=2025, month=9, day=1)

        with self.assertRaisesMessage(
            ValidationError,
            "Das Start-Datum (01.09.2025) muss vor dem End-Datum (27.07.2025) liegen.",
        ):
            self._validate(
                action=SubscriptionDateChangeApplier.ACTION_CHANGE_END,
                date=datetime.date(year=2025, month=7, day=27),
            )

    def test_validate_dateUnchanged_raisesError(self, _: MagicMock):
        with self.assertRaisesMessage(ValidationError, "Keine Änderungen"):
            self._validate(
                action=SubscriptionDateChangeApplier.ACTION_CHANGE_END,
                date=self.subscription.end_date,
            )

    def test_validate_dateOutsideGrowingPeriod_raisesError(self, _: MagicMock):
        with self.assertRaisesMessage(
            ValidationError, "Das Datum muss in der Vertragsperiode liegen"
        ):
            self._validate(
                action=SubscriptionDateChangeApplier.ACTION_CHANGE_END,
                date=datetime.date(year=2026, month=1, day=4),
            )

    def test_validate_newStartIsNeitherMondayNorPeriodStart_raisesError(
        self, _: MagicMock
    ):
        with self.assertRaisesMessage(
            ValidationError,
            "Der Vertragsbeginn muss ein Montag oder der erste Tag der Vertragsperiode sein",
        ):
            self._validate(
                action=SubscriptionDateChangeApplier.ACTION_CHANGE_START,
                date=datetime.date(year=2025, month=3, day=4),
            )

    def test_validate_newEndIsNeitherSundayNorPeriodEnd_raisesError(self, _: MagicMock):
        with self.assertRaisesMessage(
            ValidationError,
            "Das Vertragsende muss ein Sonntag oder der letzte Tag der Vertragsperiode sein",
        ):
            self._validate(
                action=SubscriptionDateChangeApplier.ACTION_CHANGE_END,
                date=datetime.date(year=2025, month=11, day=28),
            )

    @patch.object(
        TapirCache, "get_all_subscriptions_for_member", autospec=True, return_value=[]
    )
    def test_validate_newStartIsPeriodStartOnAWednesday_noError(
        self, _: MagicMock, __: MagicMock
    ):
        self.subscription.start_date = datetime.date(year=2025, month=3, day=3)

        self._validate(
            action=SubscriptionDateChangeApplier.ACTION_CHANGE_START,
            date=datetime.date(year=2025, month=1, day=1),
        )

    @patch.object(
        TapirCache, "get_all_subscriptions_for_member", autospec=True, return_value=[]
    )
    def test_validate_currentStartIsNotAMondayAndEndChanged_noError(
        self, _: MagicMock, __: MagicMock
    ):
        self.subscription.start_date = datetime.date(year=2025, month=3, day=5)

        self._validate(
            action=SubscriptionDateChangeApplier.ACTION_CHANGE_END,
            date=datetime.date(year=2025, month=11, day=30),
        )

    @patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
    def test_validate_newEndOverlapsFollowUpContractOfSameProduct_raisesError(
        self, mock_get_all_subscriptions_for_member: MagicMock, _: MagicMock
    ):
        self.subscription.end_date = datetime.date(year=2025, month=6, day=29)
        follow_up_subscription = SubscriptionFactory.build(
            member=self.subscription.member,
            product=self.subscription.product,
            period=self.subscription.period,
            start_date=datetime.date(year=2025, month=6, day=30),
        )
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            follow_up_subscription,
        ]

        with self.assertRaisesMessage(
            ValidationError,
            "Der Vertrag würde sich mit dem Vertrag vom 30.06.2025 bis 31.12.2025 überschneiden.",
        ):
            self._validate(
                action=SubscriptionDateChangeApplier.ACTION_CHANGE_END,
                date=datetime.date(year=2025, month=7, day=6),
            )

    @patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
    def test_validate_endDateChangedWithOtherContractsOverlapping_noError(
        self, mock_get_all_subscriptions_for_member: MagicMock, _: MagicMock
    ):
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            SubscriptionFactory.build(
                member=self.subscription.member, period=self.subscription.period
            ),
        ]

        self._validate(
            action=SubscriptionDateChangeApplier.ACTION_CHANGE_END,
            date=datetime.date(year=2025, month=11, day=30),
            update_other_contracts=True,
        )

    @patch.object(TapirCache, "get_all_subscriptions_for_member", autospec=True)
    def test_validate_otherContractStartsAfterNewEndDate_raisesError(
        self, mock_get_all_subscriptions_for_member: MagicMock, _: MagicMock
    ):
        other_subscription = SubscriptionFactory.build(
            member=self.subscription.member,
            period=self.subscription.period,
            start_date=datetime.date(year=2025, month=6, day=2),
        )
        mock_get_all_subscriptions_for_member.return_value = [
            self.subscription,
            other_subscription,
        ]

        with self.assertRaisesMessage(
            ValidationError,
            f"Der Vertrag {other_subscription.product.name} beginnt erst am 02.06.2025, "
            "nach dem neuen Vertragsende (18.05.2025). Bitte diesen Vertrag separat anpassen.",
        ):
            self._validate(
                action=SubscriptionDateChangeApplier.ACTION_CHANGE_END,
                date=datetime.date(year=2025, month=5, day=18),
                update_other_contracts=True,
            )

    @patch.object(RenewalCancellationStatusProvider, "get_status", autospec=True)
    def test_validate_cancelRenewalAvailable_noError(
        self, mock_get_status: MagicMock, _: MagicMock
    ):
        mock_get_status.return_value = (
            RenewalCancellationStatusProvider.STATUS_AVAILABLE
        )

        self._validate(action=SubscriptionDateChangeApplier.ACTION_CANCEL_RENEWAL)

        mock_get_status.assert_called_once_with(
            subscription=self.subscription, cache={}
        )

    @patch.object(RenewalCancellationStatusProvider, "get_status", autospec=True)
    def test_validate_cancelRenewalBeforeNoticePeriodEnd_raisesError(
        self, mock_get_status: MagicMock, _: MagicMock
    ):
        mock_get_status.return_value = (
            RenewalCancellationStatusProvider.STATUS_BEFORE_NOTICE_PERIOD_END
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Die Kündigungsfrist ist noch nicht abgelaufen. "
            "Kündigungen zum Ende der Vertragsperiode bitte über das Mitgliederprofil eintragen.",
        ):
            self._validate(action=SubscriptionDateChangeApplier.ACTION_CANCEL_RENEWAL)

    @patch.object(RenewalCancellationStatusProvider, "get_status", autospec=True)
    def test_validate_cancelRenewalNotAvailable_raisesError(
        self, mock_get_status: MagicMock, _: MagicMock
    ):
        mock_get_status.return_value = (
            RenewalCancellationStatusProvider.STATUS_NOT_AVAILABLE
        )

        with self.assertRaisesMessage(
            ValidationError, "Dieser Vertrag wird nicht verlängert"
        ):
            self._validate(action=SubscriptionDateChangeApplier.ACTION_CANCEL_RENEWAL)
