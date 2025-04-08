import datetime

from django.core.exceptions import ImproperlyConfigured

from tapir.accounts.models import EmailChangeRequest, TapirUser
from tapir.log.models import LogEntry
from tapir.utils.config import Organization
from tapir.utils.services.test_configuration_generator import TestConfigurationGenerator
from tapir.utils.services.test_joker_generator import TestJokerGenerator
from tapir.utils.services.test_pickup_location_generator import (
    TestPickupLocationGenerator,
)
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
    PickupLocation,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestDataGenerator:
    GENERATE_TEST_DATA_FOR = Organization.BIOTOP

    @staticmethod
    def clear():
        print("Clearing data...")

        model_classes = [
            PickupLocation,
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
    def generate_all(cls, override_generate_test_data_for: Organization | None = None):
        generate_test_data_for = cls.GENERATE_TEST_DATA_FOR
        if override_generate_test_data_for:
            generate_test_data_for = override_generate_test_data_for

        cls.generate_growing_periods(generate_test_data_for)
        TestProductGenerator.generate_product_data(generate_test_data_for)
        TestPickupLocationGenerator.generate_pickup_locations(generate_test_data_for)
        TestUserGenerator.generate_users_and_subscriptions()
        TestConfigurationGenerator.update_settings_for_organization(
            generate_test_data_for
        )
        TestJokerGenerator.generate_jokers()

    @classmethod
    def generate_growing_periods(cls, generate_test_data_for: Organization):
        today = datetime.date.today()
        start_date_current_period = today.replace(
            day=1,
            month=cls.get_starting_month_for_growing_period(generate_test_data_for),
        )
        if start_date_current_period > today:
            start_date_current_period = start_date_current_period.replace(
                year=start_date_current_period.year - 1
            )

        end_date_current_period = start_date_current_period.replace(
            year=start_date_current_period.year + 1
        ) - datetime.timedelta(days=1)

        # Current period
        current_period = GrowingPeriodFactory.build(
            start_date=start_date_current_period, end_date=end_date_current_period
        )

        # Previous period
        previous_period = GrowingPeriodFactory.build(
            start_date=start_date_current_period.replace(
                year=start_date_current_period.year - 1
            ),
            end_date=end_date_current_period.replace(
                year=end_date_current_period.year - 1
            ),
        )

        # Next period
        next_period = GrowingPeriodFactory.build(
            start_date=start_date_current_period.replace(
                year=start_date_current_period.year + 1
            ),
            end_date=end_date_current_period.replace(
                year=end_date_current_period.year + 1
            ),
        )

        GrowingPeriod.objects.bulk_create(
            [previous_period, current_period, next_period]
        )

    @classmethod
    def get_starting_month_for_growing_period(
        cls, generate_test_data_for: Organization
    ):
        if generate_test_data_for == Organization.BIOTOP:
            return 1
        if generate_test_data_for == Organization.WIRGARTEN:
            return 7
        raise ImproperlyConfigured(
            f"Unknown organization for test data generation: {generate_test_data_for}"
        )
