from tapir.configuration.models import TapirParameter
from tapir.subscriptions.models import NoticePeriod
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests.factories import ProductTypeFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestNoticePeriodManager(TapirIntegrationTest):
    def setUp(self):
        ParameterDefinitions().import_definitions()

    def test_setNoticePeriodDuration_noticePeriodObjectAlreadyExists_existingObjectUpdated(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        notice_period = NoticePeriod.objects.create(
            product_type=product_type,
            growing_period=growing_period,
            duration_in_months=2,
        )

        NoticePeriodManager.set_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
            notice_period_duration=3,
        )

        self.assertEqual(1, NoticePeriod.objects.count())
        notice_period.refresh_from_db()
        self.assertEqual(3, notice_period.duration_in_months)

    def test_setNoticePeriodDuration_noticePeriodObjectDoesntExists_objectCreated(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()

        NoticePeriodManager.set_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
            notice_period_duration=3,
        )

        self.assertEqual(1, NoticePeriod.objects.count())
        notice_period = NoticePeriod.objects.get()
        self.assertEqual(product_type, notice_period.product_type)
        self.assertEqual(growing_period, notice_period.growing_period)
        self.assertEqual(3, notice_period.duration_in_months)

    def test_getNoticePeriodDuration_noticePeriodObjectDoesntExist_returnsDefaultValue(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=5)

        result = NoticePeriodManager.get_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
        )

        self.assertEqual(5, result)

    def test_getNoticePeriodDuration_noticePeriodObjectExists_returnsCustomValue(
        self,
    ):
        product_type = ProductTypeFactory.create()
        growing_period = GrowingPeriodFactory.create()
        TapirParameter.objects.filter(
            key=Parameter.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=5)
        NoticePeriod.objects.create(
            product_type=product_type,
            growing_period=growing_period,
            duration_in_months=2,
        )

        result = NoticePeriodManager.get_notice_period_duration(
            product_type=product_type,
            growing_period=growing_period,
        )

        self.assertEqual(2, result)
