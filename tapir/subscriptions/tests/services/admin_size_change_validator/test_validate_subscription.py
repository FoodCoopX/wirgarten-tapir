import datetime

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestAdminSizeChangeValidatorValidateSubscription(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.member = MemberFactory.build()
        self.subscription = SubscriptionFactory.build(
            member=self.member,
            period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2027, month=1, day=1),
                end_date=datetime.date(year=2027, month=12, day=31),
            ),
        )

    def test_validateSubscription_validSubscriptionAndDate_doesNotRaise(self):
        AdminSizeChangeValidator.validate_subscription(
            member=self.member,
            subscription=self.subscription,
            change_date=datetime.date(year=2027, month=6, day=7),
        )

    def test_validateSubscription_subscriptionOfOtherMember_raisesValidationError(
        self,
    ):
        with self.assertRaisesMessage(
            ValidationError, "Dieser Vertrag gehört nicht zu diesem Mitglied."
        ):
            AdminSizeChangeValidator.validate_subscription(
                member=MemberFactory.build(),
                subscription=self.subscription,
                change_date=datetime.date(year=2027, month=6, day=7),
            )

    def test_validateSubscription_subscriptionCancelled_raisesValidationError(self):
        self.subscription.cancellation_ts = datetime.datetime(year=2027, month=3, day=1)

        with self.assertRaisesMessage(ValidationError, "bereits gekündigt"):
            AdminSizeChangeValidator.validate_subscription(
                member=self.member,
                subscription=self.subscription,
                change_date=datetime.date(year=2027, month=6, day=7),
            )

    def test_validateSubscription_dateBeforeStart_raisesValidationError(self):
        self.subscription.start_date = datetime.date(year=2027, month=7, day=5)

        with self.assertRaisesMessage(ValidationError, "innerhalb der Laufzeit"):
            AdminSizeChangeValidator.validate_subscription(
                member=self.member,
                subscription=self.subscription,
                change_date=datetime.date(year=2027, month=6, day=7),
            )

    def test_validateSubscription_dateAfterEnd_raisesValidationError(self):
        with self.assertRaisesMessage(ValidationError, "innerhalb der Laufzeit"):
            AdminSizeChangeValidator.validate_subscription(
                member=self.member,
                subscription=self.subscription,
                change_date=datetime.date(year=2028, month=1, day=3),
            )
