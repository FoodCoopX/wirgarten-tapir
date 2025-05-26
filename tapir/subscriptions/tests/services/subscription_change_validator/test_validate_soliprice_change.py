import datetime
from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.utils import timezone

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import SubscriptionFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestValidateSolipriceChange(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(
            key=ParameterKeys.HARVEST_MEMBERS_ARE_ALLOWED_TO_CHANGE_SOLIPRICE
        ).update(value=False)

    def test_validateSolipriceChange_useIsAdmin_noErrorRaised(self):
        SubscriptionChangeValidator.validate_soliprice_change(
            form=Mock(),
            field_prefix=Mock(),
            member_id=Mock(),
            logged_in_user_is_admin=True,
            subscription_start_date=Mock(),
            cache=Mock(),
        )

    def test_validateSolipriceChange_configSaysChangesAreAllowed_noErrorRaised(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.HARVEST_MEMBERS_ARE_ALLOWED_TO_CHANGE_SOLIPRICE
        ).update(value=True)

        form = Mock()
        cache = {}

        SubscriptionChangeValidator.validate_soliprice_change(
            form=form,
            field_prefix=Mock(),
            member_id=Mock(),
            logged_in_user_is_admin=False,
            subscription_start_date=Mock(),
            cache=cache,
        )

        form.build_solidarity_fields.assert_not_called()

    def test_validateSolipriceChange_soliChangedOnOneProduct_errorRaised(self):
        form = Mock()
        cache = {}
        subscription = SubscriptionFactory.create(solidarity_price_percentage=0.05)
        form.cleaned_data = {
            subscription.product.name: subscription.quantity,
            "solidarity_price_choice": 0.1,
        }
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": 0.1,
        }

        with self.assertRaises(ValidationError):
            SubscriptionChangeValidator.validate_soliprice_change(
                form=form,
                field_prefix="",
                member_id=subscription.member_id,
                logged_in_user_is_admin=False,
                subscription_start_date=subscription.start_date,
                cache=cache,
            )

    def test_validateSolipriceChange_subscriptionStartsInNextGrowingPeriod_noErrorRaised(
        self,
    ):
        form = Mock()
        cache = {}
        current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1),
            end_date=datetime.date(year=2024, month=12, day=31),
        )
        next_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
        )
        mock_timezone(
            self,
            timezone.now().replace(
                year=current_growing_period.start_date.year,
                month=current_growing_period.start_date.month,
                day=10,
            ),
        )
        subscription = SubscriptionFactory.create(
            solidarity_price_percentage=0.05, period=next_growing_period
        )
        form.cleaned_data = {
            subscription.product.name: subscription.quantity,
            "solidarity_price_choice": 0.1,
        }
        form.build_solidarity_fields.return_value = {
            "solidarity_price_percentage": 0.1,
        }

        SubscriptionChangeValidator.validate_soliprice_change(
            form=form,
            field_prefix="",
            member_id=subscription.member_id,
            logged_in_user_is_admin=False,
            subscription_start_date=subscription.start_date,
            cache=cache,
        )
