import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.subscriptions.services.contract_prerequisites_validator import (
    ContractPrerequisitesValidator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(AdminSizeChangeValidator, "validate_sepa_mandate", autospec=True)
@patch.object(ContractPrerequisitesValidator, "validate_banking_data", autospec=True)
@patch.object(OrderValidator, "validate_order_general", autospec=True)
@patch.object(
    ContractPrerequisitesValidator,
    "validate_pickup_location",
    autospec=True,
    return_value=PickupLocationFactory.build(),
)
@patch.object(
    AdminSizeChangeValidator, "validate_no_other_cancelled_subscription", autospec=True
)
@patch.object(AdminSizeChangeValidator, "validate_new_product", autospec=True)
@patch.object(AdminSizeChangeValidator, "validate_change_date", autospec=True)
@patch.object(AdminSizeChangeValidator, "validate_subscription", autospec=True)
class TestAdminSizeChangeValidatorValidate(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.member = MemberFactory.build()
        self.subscription = SubscriptionFactory.build(member=self.member)
        self.new_product = ProductFactory.build()
        self.change_date = datetime.date(year=2027, month=6, day=7)
        self.order = {self.new_product: 1}
        self.cache = {}

    def _validate(self):
        AdminSizeChangeValidator.validate(
            member=self.member,
            subscription=self.subscription,
            new_product=self.new_product,
            change_date=self.change_date,
            order=self.order,
            desired_pickup_location_id="desired_id",
            payment_rhythm="yearly",
            iban="NL76RABO8675663943",
            account_owner="test_account_owner",
            sepa_mandate_confirmed=True,
            cache=self.cache,
        )

    def test_validate_default_callsAllValidatorsWithCorrectParameters(
        self,
        mock_validate_subscription: MagicMock,
        mock_validate_change_date: MagicMock,
        mock_validate_new_product: MagicMock,
        mock_validate_no_other_cancelled_subscription: MagicMock,
        mock_validate_pickup_location: MagicMock,
        mock_validate_order_general: MagicMock,
        mock_validate_banking_data: MagicMock,
        mock_validate_sepa_mandate: MagicMock,
    ):
        self._validate()

        mock_validate_subscription.assert_called_once_with(
            member=self.member,
            subscription=self.subscription,
            change_date=self.change_date,
        )
        mock_validate_change_date.assert_called_once_with(
            change_date=self.change_date, cache=self.cache
        )
        mock_validate_new_product.assert_called_once_with(
            subscription=self.subscription, new_product=self.new_product
        )
        mock_validate_no_other_cancelled_subscription.assert_called_once_with(
            member=self.member,
            subscription=self.subscription,
            change_date=self.change_date,
            cache=self.cache,
        )
        mock_validate_pickup_location.assert_called_once_with(
            order=self.order,
            member=self.member,
            contract_start_date=self.change_date,
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
        mock_validate_banking_data.assert_called_once_with(
            member=self.member,
            account_owner="test_account_owner",
            iban="NL76RABO8675663943",
            payment_rhythm="yearly",
            cache=self.cache,
        )
        mock_validate_sepa_mandate.assert_called_once_with(
            iban="NL76RABO8675663943", sepa_mandate_confirmed=True
        )
