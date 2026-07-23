import datetime

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductTypeFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSubscriptionUpdateViewValidatorValidateOptionalProductCanBeOrderedWithoutRequiredProductSubscription(
    TapirIntegrationTest,
):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_validateOptionalProductCanBeOrderedWithoutRequiredProductSubscription_noOtherProductType_noErrorRaised(
        self,
    ):
        product_type = ProductTypeFactory.create()
        member = MemberFactory.create()

        SubscriptionUpdateViewValidator.validate_optional_product_can_be_ordered_without_required_product_subscription(
            product_type=product_type,
            member=member,
            contract_start_date=datetime.date(year=2010, month=1, day=1),
            cache={},
        )

    def test_validateOptionalProductCanBeOrderedWithoutRequiredProductSubscription_productTypeIsRequired_noErrorRaised(
        self,
    ):
        product_type, _ = ProductTypeFactory.create_batch(
            must_be_subscribed_to=True, size=2
        )
        member = MemberFactory.create()

        SubscriptionUpdateViewValidator.validate_optional_product_can_be_ordered_without_required_product_subscription(
            product_type=product_type,
            member=member,
            contract_start_date=datetime.date(year=2010, month=1, day=1),
            cache={},
        )

    def test_validateOptionalProductCanBeOrderedWithoutRequiredProductSubscription_memberHasSubscriptionToBaseProductType_returns(
        self,
    ):
        required_product_type = ProductTypeFactory.create(must_be_subscribed_to=True)
        optional_product_type = ProductTypeFactory.create(must_be_subscribed_to=False)
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            product__type=required_product_type,
            period__start_date=datetime.date(year=2010, month=1, day=1),
        )

        SubscriptionUpdateViewValidator.validate_optional_product_can_be_ordered_without_required_product_subscription(
            product_type=optional_product_type,
            member=member,
            contract_start_date=datetime.date(year=2010, month=1, day=1),
            cache={},
        )

    def test_validateOptionalProductCanBeOrderedWithoutRequiredProductSubscription_memberDoesNotHaveSubscriptionToBaseProductType_raisesValidationError(
        self,
    ):
        ProductTypeFactory.create(must_be_subscribed_to=True, name="required_PT")
        optional_product_type = ProductTypeFactory.create(
            must_be_subscribed_to=False, name="optional_PT"
        )
        member = MemberFactory.create()

        with self.assertRaises(ValidationError) as error:
            SubscriptionUpdateViewValidator.validate_optional_product_can_be_ordered_without_required_product_subscription(
                product_type=optional_product_type,
                member=member,
                contract_start_date=datetime.date(year=2010, month=1, day=1),
                cache={},
            )

        self.assertEqual(
            "Um Anteile von diese zusätzliche Produkte (optional_PT) zu bestellen, "
            "musst du Anteile von der Basis-Produkt (required_PT) an der gleiche Vertragsperiode haben.",
            error.exception.message,
        )
