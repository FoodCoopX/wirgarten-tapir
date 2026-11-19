import datetime
import json
import os
import pathlib
import random
from decimal import Decimal
from math import floor
from typing import List, Set

from django.db.models import F
from faker import Faker
from tapir_mail.service.shortcuts import make_timezone_aware

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.associations.models import AssociationMembershipType, AssociationMembership
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.log.models import LogEntry
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.config import Organization
from tapir.utils.json_user import JsonUser
from tapir.utils.models import copy_user_info
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_timezone_aware_datetime, get_from_cache_or_compute
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import (
    Member,
    GrowingPeriod,
    Subscription,
    PickupLocation,
    MemberPickupLocation,
    Product,
    CoopShareTransaction,
    OrderFeedback,
    MandateReference,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_next_growing_period
from tapir.wirgarten.tasks import assign_member_numbers
from tapir.wirgarten.utils import (
    get_today,
    legal_status_is_cooperative,
    legal_status_is_association,
    get_now,
)


class UserGenerator:
    YEARLY_CANCELLATION_PROBABILITY = 0.12
    PRICE_OVERRIDE_PROBABILITY = 0.005
    PRICE_EXEMPTION_PROBABILITY = 0.005
    TRIAL_DISABLED_PROBABILITY = 0.02
    SEASON_START_ORDER_WINDOW = datetime.timedelta(weeks=12)
    SEASON_START_ORDER_PROBABILITY = 0.8
    EXTRA_COOP_SHARES_PROBABILITY = 0.25
    CREATED_BY_ADMIN_PROBABILITY = 0.3
    MISSING_PAYMENT_RHYTHM_PROBABILITY = 0.02

    @classmethod
    def get_past_growing_period(cls, cache: dict):
        return get_from_cache_or_compute(
            cache,
            "past_growing_period",
            lambda: GrowingPeriod.objects.order_by("start_date").first(),
        )

    @staticmethod
    def get_test_users():
        path_to_json_file = os.path.join(
            pathlib.Path(__file__).parent.absolute(), "test_users.json"
        )
        file = open(path_to_json_file, encoding="UTF-8")
        json_string = file.read()
        file.close()

        return json.loads(json_string)["results"]

    @classmethod
    def get_user_count(cls, organization: Organization):
        if organization == Organization.BIOTOP:
            return 250
        if organization == Organization.BAKERY:
            return 60
        return 200

    @classmethod
    def generate_users_and_subscriptions(cls, organization: Organization):
        user_count = cls.get_user_count(organization)
        # Users generated with https://randomuser.me
        print(f"Creating {user_count} users, this may take a while")
        random.seed("wirgarten")

        fake = Faker("de_DE")

        parsed_users = cls.get_test_users()

        cache = {}

        products_from_required_types = list(
            Product.objects.filter(type__must_be_subscribed_to=True).select_related(
                "type"
            )
        )
        products_from_optional_types = list(
            Product.objects.filter(type__must_be_subscribed_to=False).select_related(
                "type"
            )
        )

        members_that_need_a_pickup_location = set()

        for index, parsed_user in enumerate(parsed_users[:user_count]):
            if (index + 1) % 20 == 0:
                print(f"\t{index+1}/{user_count}...")
            cls.generate_user(
                parsed_user=parsed_user,
                cache=cache,
                fake=fake,
                products_from_base_type=products_from_required_types,
                additional_products=products_from_optional_types,
                members_that_need_a_pickup_location=members_that_need_a_pickup_location,
            )
            CoopShareTransaction.objects.filter(
                valid_at__lte=get_today(cache=cache) - datetime.timedelta(days=60)
            ).update(admin_confirmed=get_now(cache=cache))

        cls.link_members_to_pickup_location(
            members_that_need_a_pickup_location, organization=organization
        )
        assign_member_numbers()

        # The creation date of subscriptions is used when generating payments , so we have to set a realistic date.
        Subscription.objects.update(created_at=F("start_date"))

        AutomaticSubscriptionRenewalService.renew_subscriptions_if_necessary()

    @classmethod
    def generate_user(
        cls,
        parsed_user,
        cache,
        fake,
        products_from_base_type,
        additional_products,
        members_that_need_a_pickup_location,
    ):
        json_user = JsonUser.from_parsed_user(parsed_user)
        json_user.date_joined = get_timezone_aware_datetime(
            cls.get_random_date_in_range_biased_towards_lower_end(
                cls.get_past_growing_period(cache).start_date, get_today(cache)
            ),
            datetime.time(hour=random.randint(0, 23), minute=random.randint(0, 59)),
        )

        member_without_subscriptions = random.random() < 0.20
        created_by_admin = (
            member_without_subscriptions
            and random.random() < cls.CREATED_BY_ADMIN_PROBABILITY
        )

        is_superuser = json_user.get_username() == "roberto.cortes"
        member = Member(
            is_superuser=is_superuser,
            is_staff=is_superuser,
            is_active=True,
            date_joined=json_user.date_joined,
            iban="" if created_by_admin else fake["de_DE"].iban(),
            account_owner="" if created_by_admin else json_user.get_full_name(),
            sepa_consent=None if created_by_admin else json_user.date_joined,
            privacy_consent=json_user.date_joined,
            withdrawal_consent=json_user.date_joined,
        )
        copy_user_info(json_user, member)
        member.username = member.email
        member.save()
        member.created_at = json_user.date_joined
        member.save()
        KeycloakUserManager.create_keycloak_user_if_necessary(
            user=member,
            initial_password=member.email.split("@")[0],
        )

        min_coop_shares = 0
        if not member_without_subscriptions:
            min_coop_shares, needs_pickup_location = cls.create_contracts_for_member(
                member=member,
                base_products=products_from_base_type,
                additional_products=additional_products,
                cache=cache,
            )
            if needs_pickup_location:
                members_that_need_a_pickup_location.add(member)

        if not member_without_subscriptions and random.random() < 0.3:
            cls.generate_feedback_for_member(member)

        if legal_status_is_cooperative(cache=cache):
            cls.create_coop_shares_for_user(member, min_coop_shares, cache)
        elif (
            legal_status_is_association(cache=cache)
            and not member_without_subscriptions
        ):
            cls.create_association_membership(member, cache=cache)

        if created_by_admin or (
            not member_without_subscriptions
            and random.random() < cls.MISSING_PAYMENT_RHYTHM_PROBABILITY
        ):
            return

        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            rhythm=random.choice(MemberPaymentRhythm.Rhythm.choices)[0],
            valid_from=cls.get_random_date_in_range_biased_towards_lower_end(
                lower_boundary=member.date_joined.date(),
                upper_boundary=get_today(cache=cache),
            ),
            cache=cache,
            actor=None,
        )

    @classmethod
    def get_random_date_in_range_biased_towards_lower_end(
        cls, lower_boundary: datetime.date, upper_boundary: datetime.date
    ):
        nb_days_range = (upper_boundary - lower_boundary).days
        nb_days = min([random.randint(0, nb_days_range) for _ in range(3)])
        return lower_boundary + datetime.timedelta(days=nb_days)

    @classmethod
    def create_contracts_for_member(
        cls,
        member: Member,
        base_products: List[Product],
        additional_products: List[Product],
        cache: dict,
    ) -> tuple[int, bool]:
        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member, cache=cache
        )
        today = get_today(cache=cache)
        base_order_date = cls.get_random_date_in_range_biased_towards_lower_end(
            lower_boundary=member.date_joined.date(), upper_boundary=today
        )
        base_start_date = cls.get_contract_start_date(
            order_date=base_order_date, cache=cache
        )

        chains = []
        min_coop_shares = 0
        number_of_base_products = random.choices(
            population=[1, 2], weights=[100, 1], k=1
        )[0]
        for product in random.sample(
            base_products, k=min(number_of_base_products, len(base_products))
        ):
            quantity = cls.get_random_quantity(product)
            chains.append(
                cls.build_contract_chain(
                    member=member,
                    product=product,
                    quantity=quantity,
                    start_date=base_start_date,
                    mandate_ref=mandate_ref,
                    main_contracts_by_period_id=None,
                    cache=cache,
                )
            )
            min_coop_shares += quantity * product.min_coop_shares

        if len(chains) > 0 and len(additional_products) > 0:
            main_chain = chains[0]
            main_contracts_by_period_id = {
                contract.period_id: contract for contract in main_chain
            }
            number_of_additional_products = random.choices(
                population=[0, 1, 2], weights=[50, 50, 1], k=1
            )[0]
            for product in random.sample(
                additional_products,
                k=min(number_of_additional_products, len(additional_products)),
            ):
                chain = cls.build_contract_chain(
                    member=member,
                    product=product,
                    quantity=cls.get_random_quantity(product),
                    start_date=max(
                        base_start_date,
                        cls.get_contract_start_date(
                            order_date=cls.get_random_date_in_range_biased_towards_lower_end(
                                lower_boundary=base_order_date, upper_boundary=today
                            ),
                            cache=cache,
                        ),
                    ),
                    mandate_ref=mandate_ref,
                    main_contracts_by_period_id=main_contracts_by_period_id,
                    cache=cache,
                )
                if len(chain) > 0:
                    chains.append(chain)

        Subscription.objects.bulk_create(
            [contract for chain in chains for contract in chain]
        )
        cls.create_contract_log_entries(member=member, chains=chains, cache=cache)

        needs_pickup_location = any(
            chain[0].product.type.delivery_cycle != NO_DELIVERY for chain in chains
        )
        return min_coop_shares, needs_pickup_location

    @classmethod
    def get_random_quantity(cls, product: Product) -> int:
        if product.type.single_subscription_only:
            return 1
        return random.choices([1, 2, 3], weights=[100, 1, 1], k=1)[0]

    @classmethod
    def get_contract_start_date(
        cls, order_date: datetime.date, cache: dict
    ) -> datetime.date:
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=order_date, cache=cache
        )
        next_growing_period = get_next_growing_period(
            reference_date=growing_period.end_date, cache=cache
        )
        if (
            next_growing_period is not None
            and next_growing_period.start_date - order_date
            <= cls.SEASON_START_ORDER_WINDOW
            and random.random() < cls.SEASON_START_ORDER_PROBABILITY
        ):
            return next_growing_period.start_date

        next_monday = order_date + datetime.timedelta(days=-order_date.weekday() % 7)
        if next_monday <= growing_period.end_date or next_growing_period is None:
            return next_monday
        return next_growing_period.start_date

    @classmethod
    def get_random_price_override(cls) -> Decimal | None:
        value = random.random()
        if value < cls.PRICE_EXEMPTION_PROBABILITY:
            return Decimal(0)
        if value < cls.PRICE_EXEMPTION_PROBABILITY + cls.PRICE_OVERRIDE_PROBABILITY:
            return Decimal(random.randint(10, 60))
        return None

    @classmethod
    def build_contract_chain(
        cls,
        member: Member,
        product: Product,
        quantity: int,
        start_date: datetime.date,
        mandate_ref: MandateReference,
        main_contracts_by_period_id: dict[str, Subscription] | None,
        cache: dict,
    ) -> list[Subscription]:
        today = get_today(cache=cache)
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=start_date, cache=cache
        )
        contract = Subscription(
            member=member,
            product=product,
            period=growing_period,
            quantity=quantity,
            start_date=start_date,
            end_date=growing_period.end_date,
            mandate_ref=mandate_ref,
            admin_confirmed=cls.get_confirmation_datetime(start_date, cache=cache),
            notice_period_duration=get_parameter_value(
                ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD, cache=cache
            ),
            notice_period_unit=get_parameter_value(
                ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT, cache=cache
            ),
            trial_disabled=random.random() < cls.TRIAL_DISABLED_PROBABILITY,
            price_override=cls.get_random_price_override(),
        )

        chain = []
        while True:
            main_contract = None
            if main_contracts_by_period_id is not None:
                main_contract = main_contracts_by_period_id.get(contract.period_id)
                if (
                    main_contract is None
                    or contract.start_date > main_contract.end_date
                ):
                    break

            chain.append(contract)
            if contract.start_date > today:
                break

            if main_contract is not None and main_contract.cancellation_ts is not None:
                contract.cancellation_ts = main_contract.cancellation_ts
                contract.cancellation_admin_confirmed = (
                    main_contract.cancellation_admin_confirmed
                )
                contract.end_date = min(contract.end_date, main_contract.end_date)
                break

            is_current_period = contract.period.end_date >= today
            if random.random() < cls.get_cancellation_probability(
                contract=contract, today=today
            ):
                cls.cancel_contract(
                    contract=contract,
                    cancellation_date=cls.get_random_date_in_range_biased_towards_lower_end(
                        lower_boundary=contract.start_date,
                        upper_boundary=min(contract.end_date, today),
                    ),
                    cache=cache,
                )
                break

            if is_current_period:
                break

            contract = AutomaticSubscriptionRenewalService.build_renewed_subscription(
                subscription=contract, cache=cache
            )

        return chain

    @classmethod
    def get_cancellation_probability(
        cls, contract: Subscription, today: datetime.date
    ) -> float:
        elapsed_days = (min(contract.end_date, today) - contract.start_date).days
        total_days = max(1, (contract.end_date - contract.start_date).days)
        return cls.YEARLY_CANCELLATION_PROBABILITY * elapsed_days / total_days

    @classmethod
    def cancel_contract(
        cls, contract: Subscription, cancellation_date: datetime.date, cache: dict
    ):
        contract.cancellation_ts = make_timezone_aware(
            datetime.datetime.combine(cancellation_date, datetime.time(hour=12))
        )
        contract.cancellation_admin_confirmed = cls.get_confirmation_datetime(
            cancellation_date, cache=cache
        )
        if TrialPeriodManager.is_contract_in_trial(
            contract=contract, reference_date=cancellation_date, cache=cache
        ):
            contract.end_date = min(
                contract.end_date,
                TrialPeriodManager.get_earliest_trial_cancellation_date(
                    contract=contract, reference_date=cancellation_date, cache=cache
                ),
            )

    @classmethod
    def create_contract_log_entries(
        cls, member: Member, chains: list[list[Subscription]], cache: dict
    ):
        log_entry_dates = []
        for chain in chains:
            first_contract = chain[0]
            log_entry = SubscriptionChangeLogEntry().populate_subscription_changed(
                actor=member,
                user=member,
                change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.ADDED,
                subscriptions=[first_contract],
                admin_confirmed=first_contract.admin_confirmed,
            )
            log_entry.save()
            log_entry_dates.append(
                (
                    log_entry,
                    make_timezone_aware(
                        datetime.datetime.combine(
                            min(first_contract.start_date, get_today(cache=cache)),
                            datetime.time(hour=10),
                        )
                    ),
                )
            )

            cancelled_contract = chain[-1]
            if cancelled_contract.cancellation_ts is None:
                continue
            log_entry = SubscriptionChangeLogEntry().populate_subscription_changed(
                actor=member,
                user=member,
                change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
                subscriptions=[cancelled_contract],
                admin_confirmed=cancelled_contract.cancellation_admin_confirmed,
            )
            log_entry.save()
            log_entry_dates.append((log_entry, cancelled_contract.cancellation_ts))

        for log_entry, created_date in log_entry_dates:
            log_entry.created_date = created_date
        LogEntry.objects.bulk_update(
            [
                LogEntry(id=log_entry.id, created_date=created_date)
                for log_entry, created_date in log_entry_dates
            ],
            ["created_date"],
        )

    @classmethod
    def create_coop_shares_for_user(cls, member: Member, min_shares: int, cache: dict):
        shares = min_shares
        if random.random() < cls.EXTRA_COOP_SHARES_PROBABILITY:
            shares += random.randint(1, 3)

        shares = max(1, shares)

        CoopSharePurchaseHandler.buy_cooperative_shares(
            quantity=shares,
            member=member,
            shares_valid_at=member.date_joined.date(),
            cache=cache,
            actor=None,
            pay_in_instalments=False,
        )

    @classmethod
    def create_association_membership(cls, member: Member, cache: dict):
        AssociationMembershipChangeHandler.start_membership(
            member=member,
            association_membership_type=AssociationMembershipType.objects.order_by(
                "?"
            ).first(),
            start_date=Subscription.objects.filter(member=member)
            .order_by("start_date")
            .first()
            .start_date,
            actor=None,
            cache=cache,
        )

        cancelled_subscription = (
            Subscription.objects.filter(member=member, cancellation_ts__isnull=False)
            .order_by("end_date")
            .last()
        )
        if cancelled_subscription is not None:
            AssociationMembership.objects.filter(member=member).update(
                end_date=cancelled_subscription.end_date,
                cancellation_ts=cancelled_subscription.cancellation_ts,
            )

    @classmethod
    def link_members_to_pickup_location(
        cls,
        members_that_need_a_pickup_location: Set[Member],
        organization: Organization,
    ):
        names_of_locations_that_must_be_full = []
        if organization == Organization.BIOTOP:
            names_of_locations_that_must_be_full = [
                "Grünes Warenhaus",
                "Biotop-Hofpunkt",
                "Hochalmstraße Lenggries",
            ]
        locations_that_must_be_full = list(
            PickupLocation.objects.filter(name__in=names_of_locations_that_must_be_full)
        )
        locations_that_should_not_be_full = list(
            PickupLocation.objects.exclude(
                name__in=names_of_locations_that_must_be_full
            )
        )

        member_pickup_locations = []
        for index, member in enumerate(members_that_need_a_pickup_location):
            if floor(index / 50) >= len(locations_that_must_be_full):
                pickup_location = random.choice(locations_that_should_not_be_full)
            else:
                pickup_location = random.choice(locations_that_must_be_full)
            member_pickup_locations.append(
                MemberPickupLocation(
                    member=member,
                    pickup_location=pickup_location,
                    valid_from=member.date_joined.date(),
                )
            )

        fake = Faker("de_DE")
        members_with_home_delivery = [
            member_pickup_location.member
            for member_pickup_location in member_pickup_locations
            if member_pickup_location.pickup_location.is_home_delivery
        ]
        for member in members_with_home_delivery:
            cls.fill_delivery_address(member=member, fake=fake)
        Member.objects.bulk_update(
            members_with_home_delivery,
            [
                "delivery_same_as_billing_address",
                "delivery_street",
                "delivery_postcode",
                "delivery_city",
            ],
        )
        MemberPickupLocation.objects.bulk_create(member_pickup_locations)

    @classmethod
    def fill_delivery_address(cls, member: Member, fake: Faker):
        if random.random() < 0.5:
            member.delivery_same_as_billing_address = True
            return
        member.delivery_same_as_billing_address = False
        member.delivery_street = fake.street_address()
        member.delivery_postcode = fake.postcode()
        member.delivery_city = fake.city()

    @classmethod
    def get_confirmation_datetime(cls, reference_date: datetime.date, cache: dict):
        confirmation_date = reference_date + datetime.timedelta(days=1)
        confirmation_datetime = datetime.datetime.combine(
            confirmation_date, datetime.time()
        )
        confirmation_datetime = make_timezone_aware(confirmation_datetime)
        if confirmation_date <= get_today(cache=cache):
            return confirmation_datetime
        return None

    @classmethod
    def generate_feedback_for_member(cls, member: Member):
        cls._generate_feedback(
            member=member,
            waiting_list_entry=None,
        )

    @classmethod
    def generate_feedback_for_waiting_list_entry(cls, waiting_list_entry):
        cls._generate_feedback(
            member=None,
            waiting_list_entry=waiting_list_entry,
        )

    @classmethod
    def _generate_feedback(cls, member: Member | None, waiting_list_entry):
        feedback_options = [
            "Super Qualität, bin sehr zufrieden!",
            "Tolles Gemüse, immer wieder gerne.",
            "Die Lieferung war pünktlich und die Produkte frisch.",
            "Würde ich weiterempfehlen.",
            "Gutes Angebot, könnte aber mehr Auswahl haben.",
            "Alles super, bin Fan!",
            "Qualität war diesmal nicht ganz so gut wie sonst.",
            "Bin begeistert von der Organisation.",
            "Toller Service, danke!",
            "Freue mich auf die nächste Lieferung.",
            "Hoffe, bald Mitglied werden zu können!",
            "Warteliste ist etwas lang, aber ich warte gerne.",
        ]
        OrderFeedback.objects.create(
            member=member,
            waiting_list_entry=waiting_list_entry,
            feedback_text=random.choice(feedback_options),
        )
