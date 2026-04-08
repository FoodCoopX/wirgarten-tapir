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
        ParameterDefinitions().import_definitions(bulk_create=True)

        cls.product_type = ProductTypeFactory.create()
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=cls.product_type.id
        )

        cls.product_not_subbed_to = ProductFactory.create(type=cls.product_type)

    def setUp(self) -> None:
        super().setUp()
        self.create_member_and_subscriptions()

    def create_member_and_subscriptions(self):
        self.member = MemberFactory.create()
        self.subscription_1 = SubscriptionFactory.create(
            product__type=self.product_type,
            member=self.member,
        )
        self.subscription_2 = SubscriptionFactory.create(
            product__type=self.product_type,
            member=self.member,
        )

    def test_validateAtLeastOneChange_noChanges_raisesError(self):
        form = Mock()
        cache = {}

        form.cleaned_data = {
            self.subscription_1.product.name: self.subscription_1.quantity,
            self.subscription_2.product.name: self.subscription_2.quantity,
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
        }

        SubscriptionChangeValidator.validate_at_least_one_change(
            form=form,
            field_prefix="",
            member_id=self.member.id,
            subscription_start_date=self.subscription_1.start_date,
            cache=cache,
        )
