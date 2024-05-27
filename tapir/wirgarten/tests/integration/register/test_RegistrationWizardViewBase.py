import datetime

from django.template.response import TemplateResponse
from formtools.wizard.views import StepsHelper

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import Product
from tapir.wirgarten.parameters import (
    Parameter,
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
    def setUp(self):
        ParameterDefinitions().import_definitions()

    def create_growing_period_with_one_subscription(self, year: int):
        self.product: Product = ProductFactory.create()
        param = TapirParameter.objects.get(pk=Parameter.COOP_BASE_PRODUCT_TYPE)
        param.value = self.product.type.id
        param.save()

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=year, month=1, day=1),
            end_date=datetime.date(year=year, month=12, day=31),
        )
        ProductCapacityFactory.create(
            period=growing_period, product_type=self.product.type, capacity=100
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
            price=75, product=self.product, valid_from=growing_period.start_date
        )

        response: TemplateResponse = self.client.get("/wirgarten/register")
        steps_helper: StepsHelper = response.context_data["wizard"]["steps"]

        self.assertNotIn(STEP_BASE_PRODUCT, steps_helper.all)
        self.assertIn(STEP_BASE_PRODUCT_NOT_AVAILABLE, steps_helper.all)

    def test_RegistrationWizardViewBase_currentGrowingPeriodHasFreeCapacity_showsBaseProductStep(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2023, month=6, day=1))
        growing_period = self.create_growing_period_with_one_subscription(2023)
        ProductPriceFactory.create(
            price=50, product=self.product, valid_from=growing_period.start_date
        )

        response: TemplateResponse = self.client.get("/wirgarten/register")
        steps_helper: StepsHelper = response.context_data["wizard"]["steps"]

        self.assertIn(STEP_BASE_PRODUCT, steps_helper.all)
        self.assertNotIn(STEP_BASE_PRODUCT_NOT_AVAILABLE, steps_helper.all)

    def test_RegistrationWizardViewBase_contractStartDateIsOnTheFollowingGrowingPeriod_checkTheFollowingGrowingPeriod(
        self,
    ):
        mock_timezone(self, datetime.datetime(year=2023, month=12, day=21))
        current_growing_period = self.create_growing_period_with_one_subscription(2023)
        next_growing_period = self.create_growing_period_with_one_subscription(2024)
        ProductPriceFactory.create(
            price=75, product=self.product, valid_from=current_growing_period.start_date
        )
        ProductPriceFactory.create(
            price=25, product=self.product, valid_from=next_growing_period.start_date
        )

        response: TemplateResponse = self.client.get("/wirgarten/register")
        steps_helper: StepsHelper = response.context_data["wizard"]["steps"]

        self.assertIn(STEP_BASE_PRODUCT, steps_helper.all)
        self.assertNotIn(STEP_BASE_PRODUCT_NOT_AVAILABLE, steps_helper.all)
