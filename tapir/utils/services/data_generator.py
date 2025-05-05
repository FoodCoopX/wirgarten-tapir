import datetime

import factory.random
from django.core.exceptions import ImproperlyConfigured

from tapir.accounts.models import EmailChangeRequest
from tapir.log.models import LogEntry
from tapir.utils.config import Organization
from tapir.utils.services.configuration_generator import ConfigurationGenerator
from tapir.utils.services.joker_generator import JokerGenerator
from tapir.utils.services.pickup_location_generator import (
    PickupLocationGenerator,
)
from tapir.utils.services.product_generator import ProductGenerator
from tapir.utils.services.user_generator import UserGenerator
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
    MemberPickupLocation,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class DataGenerator:
    @staticmethod
    def clear():
        print("Clearing data...")

        model_classes = [
            MemberPickupLocation,
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
        ]

        for model_class in model_classes:
            models = model_class.objects.all()
            models.delete()

        Member.objects.filter(email__endswith="@example.com").delete()

        print("Done")

    @classmethod
    def generate_all(cls, generate_test_data_for: Organization):
        factory.random.reseed_random("tapir")

        cls.generate_growing_periods(generate_test_data_for)
        ProductGenerator.generate_product_data(generate_test_data_for)
        PickupLocationGenerator.generate_pickup_locations(generate_test_data_for)
        ConfigurationGenerator.update_settings_for_organization(generate_test_data_for)
        UserGenerator.generate_users_and_subscriptions(generate_test_data_for)
        JokerGenerator.generate_jokers()

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
        if generate_test_data_for in [Organization.BIOTOP, Organization.VEREIN]:
            return 1
        if generate_test_data_for == Organization.WIRGARTEN:
            return 7
        raise ImproperlyConfigured(
            f"Unknown organization for test data generation: {generate_test_data_for}"
        )
