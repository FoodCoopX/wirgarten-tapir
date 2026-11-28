import datetime

import factory.random
from django.core.management import call_command
from tapir.mail.models import EmailConfiguration, EmailConfigurationVersion

from tapir.accounts.models import EmailChangeRequest
from tapir.accounts.services.keycloak_user_delete_service import (
    KeycloakUserDeleteService,
)
from tapir.associations.models import AssociationMembership, AssociationMembershipType
from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    Bread,
    BreadCapacityPickupLocation,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    BreadSpecificsPerDeliveryDay,
    BreadsPerPickupLocationPerWeek,
    Ingredient,
    PreferenceSatisfactionLogging,
    PreferredBread,
    StoveSession,
)
from tapir.log.models import LogEntry
from tapir.payments.models import MemberCredit
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.bakery_generator import BakeryGenerator
from tapir.utils.services.test_data_generation.configuration_generator import (
    ConfigurationGenerator,
)
from tapir.utils.services.test_data_generation.joker_generator import JokerGenerator
from tapir.utils.services.test_data_generation.mail_trigger_generator import (
    MailTriggerGenerator,
)
from tapir.utils.services.test_data_generation.mailing_list_generator import (
    MailingListGenerator,
)
from tapir.utils.services.test_data_generation.member_extra_email_generator import (
    MemberExtraEmailGenerator,
)
from tapir.utils.services.test_data_generation.member_credit_generator import (
    MemberCreditGenerator,
)
from tapir.utils.services.test_data_generation.pickup_location_generator import (
    PickupLocationGenerator,
)
from tapir.utils.services.test_data_generation.product_generator import ProductGenerator
from tapir.utils.services.test_data_generation.solidarity_contribution_generator import (
    SolidarityContributionGenerator,
)
from tapir.utils.services.test_data_generation.user_generator import UserGenerator
from tapir.utils.services.test_data_generation.waiting_list_generator import (
    WaitingListGenerator,
)
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
    QuestionaireCancellationReasonResponse,
    OrderFeedback,
    LocationRoute,
)


class DataGenerator:
    @staticmethod
    def clear():
        print("Clearing data...")

        model_classes = [
            BreadDelivery,
            BreadsPerPickupLocationPerWeek,
            BreadCapacityPickupLocation,
            AvailableBreadsForDeliveryDay,
            BreadSpecificsPerDeliveryDay,
            StoveSession,
            PreferenceSatisfactionLogging,
            PreferredBread,
            BreadContent,
            Bread,
            Ingredient,
            BreadLabel,
            CoopShareTransaction,
            Payment,
            WaitingListEntry,
            MemberPickupLocation,
            LocationRoute,
            PickupLocation,
            Subscription,
            ProductCapacity,
            GrowingPeriod,
            ProductPrice,
            Product,
            ProductType,
            LogEntry,
            QuestionaireTrafficSourceResponse,
            QuestionaireCancellationReasonResponse,
            MandateReference,
            EmailChangeRequest,
            OrderFeedback,
            MemberCredit,
            AssociationMembership,
            AssociationMembershipType,
            EmailConfigurationVersion,
            EmailConfiguration,
        ]

        for model_class in model_classes:
            models = model_class.objects.all()
            models.delete()

        MailingListGenerator.delete_all_mailing_lists()

        members_to_delete = Member.objects.filter(email__endswith="@example.com")
        for member in members_to_delete:
            KeycloakUserDeleteService.delete_user_if_exists(user=member)
        members_to_delete.delete()

        print("Done")

    @classmethod
    def generate_all(
        cls, generate_test_data_for: Organization, generate_bakery_data: bool = False
    ):
        factory.random.reseed_random("tapir")

        generate_bakery_data = generate_bakery_data or (
            generate_test_data_for is Organization.BAKERY
        )

        print(f"Generating test data for {generate_test_data_for}...")
        cls.generate_growing_periods()
        print("Creating products...")
        ProductGenerator.generate_product_data(generate_test_data_for)
        print("Creating pickup locations...")
        PickupLocationGenerator.generate_pickup_locations(generate_test_data_for)
        print("Updating configuration...")
        ConfigurationGenerator.update_settings_for_organization(generate_test_data_for)
        if generate_bakery_data:
            BakeryGenerator.generate_masterdata()
        UserGenerator.generate_users_and_subscriptions(generate_test_data_for)
        if generate_bakery_data:
            BakeryGenerator.generate_week_data()
        print("Creating jokers...")
        JokerGenerator.generate_jokers()
        print("Creating waiting list...")
        WaitingListGenerator.generate_waiting_list(generate_test_data_for)
        print("Creating Solidarity contributions...")
        SolidarityContributionGenerator.generate_solidarity_contributions()
        print("Creating member credits...")
        MemberCreditGenerator.generate_member_credits()
        print("Creating payment history...")
        call_command("rebuild_payment_history", "--no-confirm")
        print("Creating required mail triggers...")
        MailTriggerGenerator.generate_required_triggers()
        print("Creating mailing lists...")
        MailingListGenerator.generate_mailing_lists()
        print("Creating extra email addresses...")
        MemberExtraEmailGenerator.generate_member_extra_emails()
        print("Test data generation done")

    @classmethod
    def generate_growing_periods(cls):
        current_year = datetime.date.today().year
        GrowingPeriod.objects.bulk_create(
            [
                GrowingPeriod(
                    start_date=datetime.date(year=year, month=1, day=1),
                    end_date=datetime.date(year=year, month=12, day=31),
                )
                for year in [current_year - 1, current_year, current_year + 1]
            ]
        )
