import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_start_date_validator import (
    AdminStartDateValidator,
)
from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.subscriptions.services.subscription_prerequisites_validator import (
    SubscriptionPrerequisitesValidator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.types import (
    AdminSizeChange,
    SubscriptionPrerequisitesInput,
)
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    SubscriptionPrerequisitesValidator, "validate_sepa_mandate", autospec=True
)
@patch.object(
    SubscriptionPrerequisitesValidator, "validate_banking_data", autospec=True
)
@patch.object(AdminSizeChangeValidator, "validate_next_period_capacity", autospec=True)
@patch.object(OrderValidator, "validate_order_general", autospec=True)
@patch.object(
    SubscriptionPrerequisitesValidator,
    "validate_pickup_location",
    autospec=True,
    return_value=PickupLocationFactory.build(),
)
@patch.object(
    AdminSizeChangeValidator, "validate_no_other_cancelled_subscription", autospec=True
)
@patch.object(AdminSizeChangeValidator, "validate_new_product", autospec=True)
@patch.object(AdminStartDateValidator, "validate_start_date", autospec=True)
@patch.object(AdminSizeChangeValidator, "validate_subscription", autospec=True)
class TestAdminSizeChangeValidatorValidate(TapirUnitTest):
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
        self.new_product = ProductFactory.build()
        self.change_date = datetime.date(year=2027, month=6, day=7)
        self.order = {self.new_product: 1}
        self.cache = {}

    def _validate(self):
        AdminSizeChangeValidator.validate(
            size_change=AdminSizeChange(
                member=self.member,
                subscription=self.subscription,
                new_product=self.new_product,
                change_date=self.change_date,
                order=self.order,
                prerequisites=SubscriptionPrerequisitesInput(
                    desired_pickup_location_id="desired_id",
                    iban="NL76RABO8675663943",
                    account_owner="test_account_owner",
                    sepa_mandate_confirmed=True,
                ),
            ),
            cache=self.cache,
        )

    def test_validate_default_callsAllValidatorsWithCorrectParameters(
        self,
        mock_validate_subscription: MagicMock,
        mock_validate_start_date: MagicMock,
        mock_validate_new_product: MagicMock,
        mock_validate_no_other_cancelled_subscription: MagicMock,
        mock_validate_pickup_location: MagicMock,
        mock_validate_order_general: MagicMock,
        mock_validate_next_period_capacity: MagicMock,
        mock_validate_banking_data: MagicMock,
        mock_validate_sepa_mandate: MagicMock,
    ):
        self._validate()

        mock_validate_subscription.assert_called_once_with(
            member=self.member,
            subscription=self.subscription,
            change_date=self.change_date,
            cache=self.cache,
        )
        mock_validate_start_date.assert_called_once_with(
            start_date=self.change_date, cache=self.cache
        )
        mock_validate_new_product.assert_called_once_with(
            subscription=self.subscription, new_product=self.new_product
        )
        mock_validate_no_other_cancelled_subscription.assert_called_once_with(
            member=self.member,
            product_type_id=self.subscription.product.type_id,
            reference_date=self.change_date,
            excluded_subscription_id=self.subscription.id,
            cache=self.cache,
        )
        mock_validate_pickup_location.assert_called_once_with(
            order=self.order,
            member=self.member,
            subscription_start_date=self.change_date,
            desired_pickup_location_id="desired_id",
            cache=self.cache,
        )
        mock_validate_order_general.assert_called_once_with(
            order=self.order,
            contract_start_date=self.change_date,
            cache=self.cache,
            member=self.member,
            pickup_location=mock_validate_pickup_location.return_value,
        )
        mock_validate_next_period_capacity.assert_called_once_with(
            member=self.member,
            product_type_id=self.subscription.product.type_id,
            reference_date=self.change_date,
            order=self.order,
            pickup_location=mock_validate_pickup_location.return_value,
            cache=self.cache,
        )
        mock_validate_banking_data.assert_called_once_with(
            member=self.member,
            account_owner="test_account_owner",
            iban="NL76RABO8675663943",
        )
        mock_validate_sepa_mandate.assert_called_once_with(
            iban="NL76RABO8675663943", sepa_mandate_confirmed=True
        )

    def test_validate_changeFromNextPeriod_doesNotValidateNextPeriodCapacity(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        ____: MagicMock,
        _____: MagicMock,
        ______: MagicMock,
        mock_validate_next_period_capacity: MagicMock,
        *___________: MagicMock,
    ):
        self.change_date = self.subscription.end_date + datetime.timedelta(days=1)

        self._validate()

        mock_validate_next_period_capacity.assert_not_called()
