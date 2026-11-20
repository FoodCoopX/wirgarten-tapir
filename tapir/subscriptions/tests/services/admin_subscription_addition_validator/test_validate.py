import datetime
from unittest.mock import patch, MagicMock

from tapir.subscriptions.services.admin_start_date_validator import (
    AdminStartDateValidator,
)
from tapir.subscriptions.services.admin_subscription_addition_validator import (
    AdminSubscriptionAdditionValidator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.subscription_prerequisites_validator import (
    SubscriptionPrerequisitesValidator,
)
from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.subscriptions.types import (
    AdminSubscriptionAddition,
    SubscriptionPrerequisitesInput,
)
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    SubscriptionPrerequisitesValidator, "validate_sepa_mandate", autospec=True
)
@patch.object(
    SubscriptionPrerequisitesValidator, "validate_banking_data", autospec=True
)
@patch.object(OrderValidator, "validate_order_general", autospec=True)
@patch.object(
    SubscriptionPrerequisitesValidator,
    "validate_pickup_location",
    autospec=True,
    return_value=PickupLocationFactory.build(),
)
@patch.object(
    SubscriptionUpdateViewValidator,
    "validate_optional_product_can_be_ordered_without_required_product_subscription",
    autospec=True,
)
@patch.object(
    AdminSubscriptionAdditionValidator,
    "validate_start_date_not_after_last_period",
    autospec=True,
)
@patch.object(AdminStartDateValidator, "validate_start_date", autospec=True)
@patch.object(
    AdminSubscriptionAdditionValidator,
    "validate_no_subscription_of_same_product",
    autospec=True,
)
@patch.object(
    AdminSubscriptionAdditionValidator, "validate_product_and_quantity", autospec=True
)
class TestAdminSubscriptionAdditionValidatorValidate(TapirUnitTest):
    def test_validate_default_callsAllValidatorsWithCorrectParameters(
        self,
        mock_validate_product: MagicMock,
        mock_validate_no_subscription_of_same_product: MagicMock,
        mock_validate_start_date: MagicMock,
        mock_validate_start_date_not_after_last_period: MagicMock,
        mock_validate_optional_product: MagicMock,
        mock_validate_pickup_location: MagicMock,
        mock_validate_order_general: MagicMock,
        mock_validate_banking_data: MagicMock,
        mock_validate_sepa_mandate: MagicMock,
    ):
        member = MemberFactory.build()
        product = ProductFactory.build()
        start_date = datetime.date(year=2027, month=6, day=7)
        cache = {}

        addition = AdminSubscriptionAddition(
            member=member,
            product=product,
            quantity=2,
            start_date=start_date,
            prerequisites=SubscriptionPrerequisitesInput(
                desired_pickup_location_id="desired_id",
                iban="NL76RABO8675663943",
                account_owner="test_account_owner",
                sepa_mandate_confirmed=True,
            ),
        )

        AdminSubscriptionAdditionValidator.validate(addition=addition, cache=cache)

        mock_validate_product.assert_called_once_with(product=product, quantity=2)
        mock_validate_no_subscription_of_same_product.assert_called_once_with(
            member=member, product=product, start_date=start_date, cache=cache
        )
        mock_validate_start_date.assert_called_once_with(
            start_date=start_date, cache=cache
        )
        mock_validate_start_date_not_after_last_period.assert_called_once_with(
            start_date=start_date, cache=cache
        )
        mock_validate_optional_product.assert_called_once_with(
            product_type=product.type,
            member=member,
            contract_start_date=start_date,
            cache=cache,
        )
        mock_validate_pickup_location.assert_called_once_with(
            order={product: 2},
            member=member,
            subscription_start_date=start_date,
            desired_pickup_location_id="desired_id",
            cache=cache,
        )
        mock_validate_order_general.assert_called_once_with(
            order={product: 2},
            contract_start_date=start_date,
            cache=cache,
            member=None,
            pickup_location=mock_validate_pickup_location.return_value,
        )
        mock_validate_banking_data.assert_called_once_with(
            member=member,
            account_owner="test_account_owner",
            iban="NL76RABO8675663943",
        )
        mock_validate_sepa_mandate.assert_called_once_with(
            iban="NL76RABO8675663943", sepa_mandate_confirmed=True
        )
