import datetime

from tapir.bestell_wizard.views import BestellWizardBaseDataApiView
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.models import WaitingListProductWish
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductCapacityFactory,
    ProductTypeFactory,
    GrowingPeriodFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildProductTypeIdsThatAreAlreadyAtCapacity(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1)
        )
        cls.product_type_1 = ProductTypeFactory.create()
        ProductCapacityFactory.create(
            product_type=cls.product_type_1, period=cls.growing_period, capacity=10
        )
        cls.product_1_m = ProductFactory.create(type=cls.product_type_1)
        ProductPriceFactory.create(
            product=cls.product_1_m, size=1, valid_from=cls.growing_period.start_date
        )
        cls.product_1_l = ProductFactory.create(type=cls.product_type_1)
        ProductPriceFactory.create(
            product=cls.product_1_l, size=2, valid_from=cls.growing_period.start_date
        )

        cls.product_type_2 = ProductTypeFactory.create()
        ProductCapacityFactory.create(
            product_type=cls.product_type_2, period=cls.growing_period, capacity=10
        )
        cls.product_2 = ProductFactory.create(type=cls.product_type_2)
        ProductPriceFactory.create(
            product=cls.product_2, size=1, valid_from=cls.growing_period.start_date
        )

    def test_buildProductTypeIdsThatAreAlreadyAtCapacity_noContracts_productNotIncluded(
        self,
    ):
        result = BestellWizardBaseDataApiView.build_product_type_ids_that_are_already_at_capacity(
            cache={},
            product_ids_that_are_already_at_capacity=[],
            contract_start_date=datetime.date(year=2023, month=3, day=17),
        )

        self.assertEqual([], result)

    def test_buildProductTypeIdsThatAreAlreadyAtCapacity_oneProductTypeIsAtCapacity_productTypeIncluded(
        self,
    ):
        SubscriptionFactory.create(
            period=self.growing_period, product=self.product_1_m, quantity=10
        )

        result = BestellWizardBaseDataApiView.build_product_type_ids_that_are_already_at_capacity(
            cache={},
            product_ids_that_are_already_at_capacity=[],
            contract_start_date=datetime.date(year=2023, month=3, day=17),
        )

        self.assertEqual([self.product_type_1.id], result)

    def test_buildProductTypeIdsThatAreAlreadyOverCapacity_oneProductTypeIsAtCapacity_productTypeIncluded(
        self,
    ):
        SubscriptionFactory.create(
            period=self.growing_period, product=self.product_2, quantity=30
        )

        result = BestellWizardBaseDataApiView.build_product_type_ids_that_are_already_at_capacity(
            cache={},
            product_ids_that_are_already_at_capacity=[],
            contract_start_date=datetime.date(year=2023, month=3, day=17),
        )

        self.assertEqual([self.product_type_2.id], result)

    def test_buildProductTypeIdsThatAreAlreadyAtCapacity_enoughCapacityForExactlyOneProduct_productTypeNotIncluded(
        self,
    ):
        SubscriptionFactory.create(
            period=self.growing_period, product=self.product_1_l, quantity=4
        )
        SubscriptionFactory.create(
            period=self.growing_period, product=self.product_1_m, quantity=1
        )

        result = BestellWizardBaseDataApiView.build_product_type_ids_that_are_already_at_capacity(
            cache={},
            product_ids_that_are_already_at_capacity=[],
            contract_start_date=datetime.date(year=2023, month=3, day=17),
        )

        self.assertEqual([], result)

    def test_buildProductTypeIdsThatAreAlreadyOverCapacity_enoughProductTypeCapacityButNotEnoughProductCapacity_productTypeIncluded(
        self,
    ):
        SubscriptionFactory.create(
            period=self.growing_period, product=self.product_1_m, quantity=2
        )

        result = BestellWizardBaseDataApiView.build_product_type_ids_that_are_already_at_capacity(
            cache={},
            product_ids_that_are_already_at_capacity=[
                self.product_1_m.id,
                self.product_1_l.id,
            ],
            contract_start_date=datetime.date(year=2023, month=3, day=17),
        )

        self.assertEqual([self.product_type_1.id], result)

    def test_buildProductTypeIdsThatAreAlreadyOverCapacity_waitingListEntryTakesCapacity_productTypeIncluded(
        self,
    ):
        SubscriptionFactory.create(
            period=self.growing_period, product=self.product_1_m, quantity=8
        )

        result = BestellWizardBaseDataApiView.build_product_type_ids_that_are_already_at_capacity(
            cache={},
            product_ids_that_are_already_at_capacity=[],
            contract_start_date=datetime.date(year=2023, month=3, day=17),
        )
        self.assertEqual([], result)

        waiting_list_entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=waiting_list_entry, product=self.product_1_m, quantity=2
        )

        result = BestellWizardBaseDataApiView.build_product_type_ids_that_are_already_at_capacity(
            cache={},
            product_ids_that_are_already_at_capacity=[],
            contract_start_date=datetime.date(year=2023, month=3, day=17),
        )
        self.assertEqual([self.product_type_1.id], result)
