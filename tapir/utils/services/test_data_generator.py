import datetime

from django.core.exceptions import ImproperlyConfigured

from tapir.accounts.models import EmailChangeRequest, TapirUser
from tapir.log.models import LogEntry
from tapir.utils.config import Organization
from tapir.utils.services.test_configuration_generator import TestConfigurationGenerator
from tapir.utils.services.test_joker_generator import TestJokerGenerator
from tapir.utils.services.test_product_generator import TestProductGenerator
from tapir.utils.services.test_user_generator import TestUserGenerator
from tapir.wirgarten.models import (
    Subscription,
    CoopShareTransaction,
    WaitingListEntry,
    QuestionaireTrafficSourceResponse,
    Payment,
    MandateReference,
    Member,
    GrowingPeriod,
    ProductType,
    ProductPrice,
    Product,
    ProductCapacity,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestDataGenerator:
    GENERATE_TEST_DATA_FOR = Organization.BIOTOP

    @staticmethod
    def clear():
        print("Clearing data...")

        model_classes = [
            Subscription,
            ProductCapacity,
            GrowingPeriod,
            ProductPrice,
            Product,
            ProductType,
            LogEntry,
            CoopShareTransaction,
            WaitingListEntry,
            QuestionaireTrafficSourceResponse,
            Payment,
            MandateReference,
            EmailChangeRequest,
            Member,
            TapirUser,
        ]

        for model_class in model_classes:
            model_class.objects.all().delete()

        print("Done")

    @classmethod
    def generate_all(cls):
        cls.generate_growing_periods()
        TestProductGenerator.generate_product_data(cls.GENERATE_TEST_DATA_FOR)
        TestUserGenerator.generate_users_and_subscriptions()
        TestConfigurationGenerator.update_settings_for_organization(
            cls.GENERATE_TEST_DATA_FOR
        )
        TestJokerGenerator.generate_jokers()

    @classmethod
    def generate_growing_periods(cls):
        today = datetime.date.today()
        start_date_current_period = today.replace(
            day=1, month=cls.get_starting_month_for_growing_period()
        )
        end_date_current_period = start_date_current_period.replace(
            year=today.year + 1
        ) - datetime.timedelta(days=1)

        # Current period
        GrowingPeriodFactory.create(
            start_date=start_date_current_period, end_date=end_date_current_period
        )

        # Previous period
        GrowingPeriodFactory.create(
            start_date=start_date_current_period.replace(
                year=start_date_current_period.year - 1
            ),
            end_date=end_date_current_period.replace(
                year=end_date_current_period.year - 1
            ),
        )

        # Next period
        GrowingPeriodFactory.create(
            start_date=start_date_current_period.replace(
                year=start_date_current_period.year + 1
            ),
            end_date=end_date_current_period.replace(
                year=end_date_current_period.year + 1
            ),
        )

    @classmethod
    def get_starting_month_for_growing_period(cls):
        if cls.GENERATE_TEST_DATA_FOR == Organization.BIOTOP:
            return 1
        if cls.GENERATE_TEST_DATA_FOR == Organization.WIRGARTEN:
            return 7
        raise ImproperlyConfigured(
            f"Unknown organization for test data generation: {cls.GENERATE_TEST_DATA_FOR}"
        )
