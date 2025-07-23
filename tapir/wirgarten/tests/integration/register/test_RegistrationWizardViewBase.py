import datetime

from django.template.response import TemplateResponse
from formtools.wizard.views import StepsHelper

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import Product
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import (
    ParameterDefinitions,
)
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    GrowingPeriodFactory,
    ProductCapacityFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from tapir.wirgarten.views.register import (
    STEP_BASE_PRODUCT,
    STEP_BASE_PRODUCT_NOT_AVAILABLE,
)


class TestRegistrationWizardViewBase(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.product: Product = ProductFactory.create()
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=cls.product.type_id
        )

    def create_growing_period_with_one_subscription(self, year: int):
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=year, month=1, day=1),
            end_date=datetime.date(year=year, month=12, day=31),
        )
        ProductCapacityFactory.create(
            period=growing_period, product_type=self.product.type, capacity=2
        )
        SubscriptionFactory.create(
            period=growing_period, quantity=1, product=self.product
        )

        return growing_period

    def test_RegistrationWizardViewBase_currentGrowingPeriodIsFull_showsWaitingList(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2023, month=6, day=1))
        growing_period = self.create_growing_period_with_one_subscription(2023)
        ProductPriceFactory.create(
            size=1.5,
            product=self.product,
            valid_from=growing_period.start_date,
        )

        response: TemplateResponse = self.client.get("/tapir/register")
        steps_helper: StepsHelper = response.context_data["wizard"]["steps"]

        self.assertNotIn(STEP_BASE_PRODUCT, steps_helper.all)
        self.assertIn(STEP_BASE_PRODUCT_NOT_AVAILABLE, steps_helper.all)

    def test_RegistrationWizardViewBase_currentGrowingPeriodHasFreeCapacity_showsBaseProductStep(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2023, month=6, day=1))
        growing_period = self.create_growing_period_with_one_subscription(2023)
        ProductPriceFactory.create(
            size=1,
            product=self.product,
            valid_from=growing_period.start_date,
        )

        response: TemplateResponse = self.client.get("/tapir/register")
        steps_helper: StepsHelper = response.context_data["wizard"]["steps"]

        self.assertIn(STEP_BASE_PRODUCT, steps_helper.all)
        self.assertNotIn(STEP_BASE_PRODUCT_NOT_AVAILABLE, steps_helper.all)
        self.assertEqual(1, len(response.context_data["form"].free_capacity))
        self.assertEqual(1.0, float(response.context_data["form"].free_capacity[0]))

    def test_RegistrationWizardViewBase_contractStartDateIsOnTheFollowingGrowingPeriod_checkTheFollowingGrowingPeriod(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2023, month=12, day=21))
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_BUFFER_TIME_BEFORE_START
        ).update(value=12)
        current_growing_period = self.create_growing_period_with_one_subscription(2023)
        next_growing_period = self.create_growing_period_with_one_subscription(2024)
        ProductPriceFactory.create(
            size=1.5, product=self.product, valid_from=current_growing_period.start_date
        )
        ProductPriceFactory.create(
            size=0.6, product=self.product, valid_from=next_growing_period.start_date
        )

        response: TemplateResponse = self.client.get("/tapir/register")
        steps_helper: StepsHelper = response.context_data["wizard"]["steps"]

        self.assertIn(STEP_BASE_PRODUCT, steps_helper.all)
        self.assertNotIn(STEP_BASE_PRODUCT_NOT_AVAILABLE, steps_helper.all)
        self.assertEqual(1, len(response.context_data["form"].free_capacity))
        self.assertEqual(1.4, float(response.context_data["form"].free_capacity[0]))

    def test_RegistrationWizardViewBase_currentGrowingPeriodHasMembersInTrial_freeCapacityShouldIncludeMembersInTrial(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2023, month=6, day=1))
        growing_period = self.create_growing_period_with_one_subscription(2023)
        ProductPriceFactory.create(
            price=40, product=self.product, valid_from=growing_period.start_date, size=1
        )
        SubscriptionFactory.create(
            period=growing_period,
            quantity=1,
            product=self.product,
            start_date=datetime.datetime(year=2023, month=6, day=15),
        )

        response: TemplateResponse = self.client.get("/tapir/register")
        steps_helper: StepsHelper = response.context_data["wizard"]["steps"]

        self.assertNotIn(STEP_BASE_PRODUCT, steps_helper.all)
        self.assertIn(STEP_BASE_PRODUCT_NOT_AVAILABLE, steps_helper.all)
