import datetime
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.forms.subscription import BaseProductForm
from tapir.wirgarten.models import Subscription, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import (
    ParameterDefinitions,
)
from tapir.wirgarten.tests.factories import (
    ProductPriceFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
    ProductCapacityFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestValidateCannotReduceSize(TapirIntegrationTest):
    NOW = timezone.make_aware(datetime.datetime(year=2024, month=3, day=15))

    def setUp(self):
        super().setUp()
        ParameterDefinitions().import_definitions()
        mock_timezone(self, self.NOW)

        product_type = ProductTypeFactory(name="Ernteanteile", delivery_cycle=WEEKLY[0])
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=product_type.id
        )

        self.product_price_s = ProductPriceFactory.create(
            size=0.8, product__name="S", product__type=product_type
        )
        self.product_price_m = ProductPriceFactory.create(
            size=1, product__name="M", product__type=product_type
        )
        self.product_price_l = ProductPriceFactory.create(
            size=1.4, product__name="L", product__type=product_type
        )
        self.current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1),
            end_date=datetime.date(year=2024, month=12, day=31),
        )

        ProductCapacityFactory.create(
            capacity=100,
            product_type=product_type,
            product_type__delivery_cycle=WEEKLY[0],
            period=self.current_growing_period,
        )

    @patch.object(BaseProductForm, "validate_pickup_location_capacity")
    @patch.object(BaseProductForm, "validate_solidarity_price")
    @patch.object(BaseProductForm, "validate_pickup_location")
    @patch.object(BaseProductForm, "validate_total_capacity")
    def test_validateCannotReduceSize_tryToReduceSizeOfRunningSubscription_formShowsError(
        self, *_
    ):
        # the other validate functions are mocked so that we don't have to setup test data for them
        # their return value is irrelevant

        subscription = SubscriptionFactory.create(
            product=self.product_price_l.product,
            period=self.current_growing_period,
            quantity=1,
        )

        url = f"{reverse('wirgarten:member_add_subscription', args=[subscription.member.id])}?productType=Ernteanteile"
        self.client.force_login(subscription.member)
        response = self.client.post(
            url,
            data={
                "growing_period": self.current_growing_period.id,
                "base_product_M": 1,
                "base_product_L": 0,
                "solidarity_price_harvest_shares": 0.0,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(1, Subscription.objects.count())
        form: BaseProductForm = response.context_data["form"]
        self.assertEqual(1, len(form.errors))
        self.assertIn("__all__", form.errors.keys())
        self.assertEqual(1, len(form.errors["__all__"]))
        self.maxDiff = 1000
        self.assertEqual(
            "Während eine Vertrag läuft es ist nur erlaubt die Größe des Vertrags zu erhöhen. "
            "Deiner aktueller Vertrag für diese Periode entspricht Größe 1.40. "
            "Deiner letzter Auswahl hier entsprach Größe 1.00.",
            form.errors["__all__"][0],
        )

    @patch.object(BaseProductForm, "validate_pickup_location_capacity")
    @patch.object(BaseProductForm, "validate_solidarity_price")
    @patch.object(BaseProductForm, "validate_pickup_location")
    @patch.object(BaseProductForm, "validate_total_capacity")
    def test_validateCannotReduceSize_tryToIncreaseSizeOfRunningSubscription_formIsValid(
        self, *_
    ):
        subscription = SubscriptionFactory.create(
            product=self.product_price_m.product,
            period=self.current_growing_period,
            quantity=1,
        )

        url = f"{reverse('wirgarten:member_add_subscription', args=[subscription.member.id])}?productType=Ernteanteile"
        self.client.force_login(subscription.member)
        response = self.client.post(
            url,
            data={
                "growing_period": self.current_growing_period.id,
                "base_product_M": 0,
                "base_product_L": 1,
                "solidarity_price_harvest_shares": 0.0,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(2, Subscription.objects.count())
        subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2024, month=3, day=31), subscription.end_date
        )
        new_subscription = Subscription.objects.exclude(id=subscription.id).get()
        self.assertEqual(
            datetime.date(year=2024, month=4, day=1), new_subscription.start_date
        )
        self.assertEqual("L", new_subscription.product.name)

    @patch.object(BaseProductForm, "validate_pickup_location_capacity")
    @patch.object(BaseProductForm, "validate_solidarity_price")
    @patch.object(BaseProductForm, "validate_pickup_location")
    @patch.object(BaseProductForm, "validate_total_capacity")
    def test_validateCannotReduceSize_tryToReduceSizeOfFutureSubscription_formIsValid(
        self, *_
    ):
        current_subscription = SubscriptionFactory.create(
            product=self.product_price_m.product,
            period=self.current_growing_period,
            quantity=1,
        )

        future_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
        )
        ProductCapacityFactory.create(
            capacity=100,
            product_type=ProductType.objects.get(),
            product_type__delivery_cycle=WEEKLY[0],
            period=future_growing_period,
        )

        future_subscription = SubscriptionFactory.create(
            product=self.product_price_l.product,
            period=future_growing_period,
            quantity=1,
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=5, day=1),
            member=current_subscription.member,
        )

        url = f"{reverse('wirgarten:member_add_subscription', args=[current_subscription.member.id])}?productType=Ernteanteile"
        self.client.force_login(current_subscription.member)
        response = self.client.post(
            url,
            data={
                "growing_period": future_growing_period.id,
                "base_product_S": 1,
                "base_product_M": 0,
                "base_product_L": 0,
                "solidarity_price_harvest_shares": 0.0,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(2, Subscription.objects.count())
        self.assertFalse(
            Subscription.objects.filter(id=future_subscription.id).exists()
        )
        new_subscription = Subscription.objects.exclude(
            id=current_subscription.id
        ).get()
        self.assertEqual(
            datetime.date(year=2025, month=1, day=1), new_subscription.start_date
        )
        self.assertEqual("S", new_subscription.product.name)
