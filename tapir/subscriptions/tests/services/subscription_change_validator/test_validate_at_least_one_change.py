from unittest.mock import Mock

from django.core.exceptions import ValidationError

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    ProductTypeFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestValidateAtLeastOneChange(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

        cls.member = MemberFactory.create()
        cls.product_type = ProductTypeFactory.create()
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=cls.product_type.id
        )
        cls.subscription_1 = SubscriptionFactory.create(
            product__type=cls.product_type, member=cls.member, solidarity_price=0.1
        )
        cls.subscription_2 = SubscriptionFactory.create(
            product__type=cls.product_type, member=cls.member, solidarity_price=0.1
        )
        cls.product_not_subbed_to = ProductFactory.create(type=cls.product_type)

    def test_validateAtLeastOneChange_noChanges_raisesError(self):
        form = Mock()
        cache = {}

        form.cleaned_data = {
            self.subscription_1.product.name: self.subscription_1.quantity,
            self.subscription_2.product.name: self.subscription_2.quantity,
            "solidarity_price_harvest_shares": 0.1,
        }
        form.build_solidarity_fields.return_value = {
            "solidarity_price": 0.1,
        }

        with self.assertRaises(ValidationError):
            SubscriptionChangeValidator.validate_at_least_one_change(
                form=form,
                field_prefix="",
                member_id=self.member.id,
                subscription_start_date=self.subscription_1.start_date,
                cache=cache,
            )

    def test_validateAtLeastOneChange_oneQuantityChange_noErrorRaised(self):
        form = Mock()
        cache = {}

        form.cleaned_data = {
            self.subscription_1.product.name: self.subscription_1.quantity,
            self.subscription_2.product.name: self.subscription_2.quantity + 1,
            "solidarity_price_harvest_shares": 0.1,
        }
        form.build_solidarity_fields.return_value = {
            "solidarity_price": 0.1,
        }

        SubscriptionChangeValidator.validate_at_least_one_change(
            form=form,
            field_prefix="",
            member_id=self.member.id,
            subscription_start_date=self.subscription_1.start_date,
            cache=cache,
        )

    def test_validateAtLeastOneChange_oneSolidarityChange_noErrorRaised(self):
        form = Mock()
        cache = {}

        form.cleaned_data = {
            self.subscription_1.product.name: self.subscription_1.quantity,
            self.subscription_2.product.name: self.subscription_2.quantity,
            "solidarity_price_harvest_shares": 0.15,
        }
        form.build_solidarity_fields.return_value = {
            "solidarity_price": 0.15,
        }

        SubscriptionChangeValidator.validate_at_least_one_change(
            form=form,
            field_prefix="",
            member_id=self.member.id,
            subscription_start_date=self.subscription_1.start_date,
            cache=cache,
        )

    def test_validateAtLeastOneChange_oneProductChange_noErrorRaised(self):
        form = Mock()
        cache = {}

        form.cleaned_data = {
            self.subscription_1.product.name: self.subscription_1.quantity,
            self.product_not_subbed_to.name: 1,
            "solidarity_price_harvest_shares": 0.1,
        }
        form.build_solidarity_fields.return_value = {
            "solidarity_price": 0.1,
        }

        SubscriptionChangeValidator.validate_at_least_one_change(
            form=form,
            field_prefix="",
            member_id=self.member.id,
            subscription_start_date=self.subscription_1.start_date,
            cache=cache,
        )
