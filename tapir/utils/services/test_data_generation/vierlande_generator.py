import datetime
import random
from decimal import Decimal

from django.db.models import F
from django.templatetags.static import static
from faker import Faker

from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembershipTypePrice,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.configuration.models import TapirParameter
from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import THEME_VIERLANDE
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.tests.factories import PickupLocationDeliveryChargeFactory
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    MemberPickupLocation,
    PickupLocation,
    PickupLocationCapability,
    PickupLocationOpeningTime,
    Product,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.tasks import assign_member_numbers
from tapir.wirgarten.tests.factories import (
    PickupLocationCapabilityFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.utils import get_today


class VierlandeGenerator:
    """
    All Solawi Vierlande specific test data: the parameters (member and share counts,
    product variants, pickup locations, membership types, city/land distribution) and
    the code that builds them.

    This is the lowest layer of the test data generation: it must not import the other
    domain generators (``ProductGenerator``, ``UserGenerator``, ...). Where it needs one
    of their generic helpers, the generator class is passed in explicitly.
    """

    TOTAL_MEMBER_COUNT = 226
    NUMBER_OF_SUPPORTING_MEMBERS = 18
    STARTING_MONTH = 3
    CITY_SHARE = Decimal("0.62")

    MEMBER_NUMBER_PREFIX = "VL"

    MEMBERSHIP_TYPE_ORDENTLICH = "ordentliches Mitglied"
    MEMBERSHIP_TYPE_FOERDER = "Fördermitglied"
    MEMBERSHIP_TYPE_ORDENTLICH_PRICE = Decimal("5.00")
    MEMBERSHIP_TYPE_FOERDER_PRICE = Decimal("0.00")

    # (name, base_price, size, count, base, description, image_file)
    # One subscription per share member: 194 * 1 + 13 * 2 + 1 * 3 = 223 assigned share
    # units of 230 capacity.
    HARVEST_SHARE_VARIANTS = [
        {
            "name": "einfach",
            "base_price": 70,
            "size": 1.0,
            "count": 194,
            "base": True,
            "description": "Der einfache Ernteanteil, etwa für eine Person.",
            "image_file": "harvest_share_small.png",
        },
        {
            "name": "groß",
            "base_price": 140,
            "size": 2.0,
            "count": 13,
            "base": False,
            "description": "Der große Ernteanteil, etwa für zwei Personen.",
            "image_file": "harvest_share_medium.png",
        },
        {
            "name": "sehr groß",
            "base_price": 210,
            "size": 3.0,
            "count": 1,
            "base": False,
            "description": "Der sehr große Ernteanteil, etwa für Familien.",
            "image_file": "harvest_share_large.png",
        },
    ]

    # (name, street, postcode, city, coords_lon, coords_lat, max_capacity, has_delivery_charge)
    # Note: despite their names, coords_lon holds the latitude and coords_lat the
    # longitude (legacy convention shared with the Leaflet maps and the other
    # organization generators).
    PICKUP_LOCATIONS = [
        # Vierlande / near Bergedorf (land, no delivery charge)
        (
            "Vierländer Freilichtmuseum Rieck Haus",
            "Curslacker Deich 284",
            "21039",
            "Hamburg-Curslack",
            53.4610,
            10.1960,
            25,
            False,
        ),
        (
            "Zollenspieker Fährhaus",
            "Zollenspieker Hauptdeich 141",
            "21037",
            "Hamburg-Kirchwerder",
            53.4140,
            10.2140,
            21,
            False,
        ),
        (
            "Schloss Bergedorf",
            "Bergedorfer Schloßstraße 4",
            "21029",
            "Hamburg-Bergedorf",
            53.4890,
            10.2110,
            29,
            False,
        ),
        (
            "St. Nicolai Altengamme",
            "Altengammer Kirchensteig 1",
            "21039",
            "Hamburg-Altengamme",
            53.4360,
            10.2460,
            17,
            False,
        ),
        # Eigene Gärtnerei
        (
            "Gärtnerei Ochsenwerder",
            "Alter Kirchdech 10",
            "21037",
            "Hamburg-Ochsenwerder",
            53.4890,
            10.2230,
            50,
            False,
        ),
        # Hamburg Innenstadt (city, with delivery charge)
        (
            "Elbphilharmonie",
            "Platz der Deutschen Einheit 1",
            "20457",
            "Hamburg",
            53.5413,
            9.9842,
            40,
            True,
        ),
        (
            "Speicherstadt",
            "Am Sandtorkai 36",
            "20457",
            "Hamburg",
            53.5450,
            9.9950,
            40,
            True,
        ),
        (
            "Hamburger Rathaus",
            "Rathausmarkt 1",
            "20095",
            "Hamburg",
            53.5503,
            9.9920,
            45,
            True,
        ),
        (
            "Landungsbrücken",
            "Sankt-Pauli-Landungsbrücken 3",
            "20359",
            "Hamburg",
            53.5459,
            9.9665,
            35,
            True,
        ),
        (
            "St. Michaelis (Michel)",
            "Englische Planke 1",
            "20459",
            "Hamburg",
            53.5484,
            9.9789,
            30,
            True,
        ),
        (
            "Binnenalster / Jungfernstieg",
            "Jungfernstieg 1",
            "20095",
            "Hamburg",
            53.5537,
            9.9928,
            40,
            True,
        ),
    ]

    CITY_PICKUP_LOCATION_NAMES = [
        name
        for name, _, _, _, _, _, _, has_delivery_charge in PICKUP_LOCATIONS
        if has_delivery_charge
    ]
    LAND_PICKUP_LOCATION_NAMES = [
        name
        for name, _, _, _, _, _, _, has_delivery_charge in PICKUP_LOCATIONS
        if not has_delivery_charge
    ]
    NUMBER_OF_SHARE_MEMBERS = sum(
        variant["count"] for variant in HARVEST_SHARE_VARIANTS
    )

    @classmethod
    def update_configuration(cls):
        TapirParameter.objects.filter(key=ParameterKeys.MEMBER_NUMBER_PREFIX).update(
            value=cls.MEMBER_NUMBER_PREFIX
        )

        for key in [
            ParameterKeys.BIDDING_ROUND_ENABLED,
            ParameterKeys.BIDDING_ROUND_URL_ENABLED,
            ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED,
            ParameterKeys.BIDDING_ROUND_STATS_INCLUDE_AUTO_RENEWED,
            ParameterKeys.BIDDING_ROUND_STATS_MEMBERSHIP_INCLUDED_IN_PRODUCT_TYPE,
        ]:
            TapirParameter.objects.filter(key=key).update(value=True)

        valid_from = GrowingPeriod.objects.order_by("start_date").first().start_date

        ordentliches_mitglied = AssociationMembershipType.objects.create(
            name=cls.MEMBERSHIP_TYPE_ORDENTLICH,
            order_in_bestell_wizard=1,
            description_in_bestell_wizard="Ordentliche Mitgliedschaft im Verein mit Stimmrecht.",
        )
        AssociationMembershipTypePrice.objects.create(
            type=ordentliches_mitglied,
            valid_from=valid_from,
            price=cls.MEMBERSHIP_TYPE_ORDENTLICH_PRICE,
        )

        foerdermitglied = AssociationMembershipType.objects.create(
            name=cls.MEMBERSHIP_TYPE_FOERDER,
            order_in_bestell_wizard=2,
            description_in_bestell_wizard="Fördermitgliedschaft zur Unterstützung des Vereins ohne Stimmrecht.",
        )
        AssociationMembershipTypePrice.objects.create(
            type=foerdermitglied,
            valid_from=valid_from,
            price=cls.MEMBERSHIP_TYPE_FOERDER_PRICE,
        )

    @staticmethod
    def _harvest_share_image(file_name: str) -> str:
        return static(f"core/themes/{THEME_VIERLANDE}/images/ernteanteile/{file_name}")

    @classmethod
    def generate_products(
        cls, product_generator, product_type_ernteanteile: ProductType
    ):
        for variant in cls.HARVEST_SHARE_VARIANTS:
            product_generator.generate_product(
                product_type=product_type_ernteanteile,
                name=variant["name"],
                base_price=variant["base_price"],
                size=variant["size"],
                base=variant["base"],
                min_coop_shares=0,
                description_in_bestellwizard=variant["description"],
                url_of_image_in_bestellwizard=cls._harvest_share_image(
                    variant["image_file"]
                ),
            )

    @classmethod
    def generate_pickup_locations(cls):
        ernteanteile = ProductType.objects.get(name="Ernteanteile")

        today = datetime.date.today()
        valid_from = today - datetime.timedelta(days=today.weekday())

        for (
            name,
            street,
            postcode,
            city,
            coords_lon,
            coords_lat,
            max_capacity,
            has_delivery_charge,
        ) in cls.PICKUP_LOCATIONS:
            pickup_location = PickupLocationFactory.create(
                name=name,
                street=street,
                postcode=postcode,
                city=city,
                coords_lon=coords_lon,
                coords_lat=coords_lat,
            )
            PickupLocationCapabilityFactory.create(
                pickup_location=pickup_location,
                max_capacity=max_capacity,
                product_type=ernteanteile,
            )
            PickupLocationOpeningTime.objects.create(
                pickup_location=pickup_location,
                day_of_week=2,
                open_time=datetime.time(hour=14),
                close_time=datetime.time(hour=19),
            )
            if has_delivery_charge:
                PickupLocationDeliveryChargeFactory.create(
                    pickup_location=pickup_location,
                    amount=Decimal("1.50"),
                    valid_from=valid_from,
                )

    @classmethod
    def get_pickup_location_groups(cls):
        city_locations = list(
            PickupLocation.objects.filter(
                name__in=cls.CITY_PICKUP_LOCATION_NAMES
            ).order_by("name")
        )
        land_locations = list(
            PickupLocation.objects.filter(
                name__in=cls.LAND_PICKUP_LOCATION_NAMES
            ).order_by("name")
        )
        return city_locations, land_locations

    @classmethod
    def distribute_entries_by_city_land(
        cls,
        weighted_entries,
        city_locations,
        land_locations,
        city_share: Decimal = None,
    ):
        """
        Assign each ``(entry, size)`` pair to a pickup location so that the summed size
        in the city locations is about ``city_share`` of the total and the remainder
        goes to the land locations. Within each group the entries are distributed
        proportionally to the depot capacities (in share units).
        """
        city_share = cls.CITY_SHARE if city_share is None else city_share

        all_locations = list(city_locations) + list(land_locations)
        if not all_locations:
            return {}

        normalized_entries = [
            (entry, Decimal(str(size))) for entry, size in weighted_entries
        ]
        total_units = sum((size for _, size in normalized_entries), Decimal("0"))
        if total_units == 0 or not city_locations or not land_locations:
            return {entry: all_locations[0] for entry, _ in normalized_entries}

        city_target = int(round(float(total_units) * float(city_share)))
        indexed_entries = sorted(
            (
                (index, entry, size)
                for index, (entry, size) in enumerate(normalized_entries)
            ),
            key=lambda item: (item[2], item[0]),
            reverse=True,
        )

        city_entries = []
        land_entries = []
        city_units = Decimal("0")
        for _, entry, size in indexed_entries:
            if city_units + size <= city_target:
                city_entries.append((entry, size))
                city_units += size
            else:
                land_entries.append((entry, size))

        return {
            **cls._assign_group_to_locations(city_entries, city_locations),
            **cls._assign_group_to_locations(land_entries, land_locations),
        }

    @staticmethod
    def _assign_group_to_locations(group_entries, locations):
        if not group_entries:
            return {}

        capacity_by_location_id = {}
        for capability in PickupLocationCapability.objects.filter(
            pickup_location__in=locations
        ):
            capacity_by_location_id[capability.pickup_location_id] = (
                capacity_by_location_id.get(capability.pickup_location_id, Decimal("0"))
                + Decimal(capability.max_capacity or 0)
            )

        ordered_locations = sorted(locations, key=lambda location: location.name)
        group_units = sum((size for _, size in group_entries), Decimal("0"))
        total_capacity = sum(
            (
                capacity_by_location_id.get(location.id, Decimal("0"))
                for location in ordered_locations
            ),
            Decimal("0"),
        )

        def target_for(location):
            if total_capacity == 0:
                return Decimal("0")
            return (
                group_units
                * capacity_by_location_id.get(location.id, Decimal("0"))
                / total_capacity
            )

        current = {location.id: Decimal("0") for location in ordered_locations}
        assignment = {}
        for entry, size in sorted(
            group_entries, key=lambda item: item[1], reverse=True
        ):
            chosen = max(
                ordered_locations,
                key=lambda location: target_for(location) - current[location.id],
            )
            assignment[entry] = chosen
            current[chosen.id] += size
        return assignment

    @classmethod
    def generate_users_and_subscriptions(cls, user_generator, organization):
        user_count = cls.TOTAL_MEMBER_COUNT
        print(f"Creating {user_count} Vierlande users, this may take a while")
        random.seed("wirgarten")
        fake = Faker("de_DE")
        parsed_users = user_generator.get_test_users()[:user_count]
        cache = {}

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=get_today(cache=cache), cache=cache
        )
        products_by_name = {
            product.name: product
            for product in Product.objects.filter(type__name="Ernteanteile")
        }

        members_with_sizes = []
        member_index = 0
        for variant in cls.HARVEST_SHARE_VARIANTS:
            product = products_by_name[variant["name"]]
            size = get_product_price(
                product=product, reference_date=get_today(cache=cache), cache=cache
            ).size
            for _ in range(variant["count"]):
                member = user_generator.create_member(
                    parsed_user=parsed_users[member_index], cache=cache, fake=fake
                )
                member_index += 1
                start_date = (
                    user_generator.get_random_date_in_range_biased_towards_lower_end(
                        growing_period.start_date, get_today(cache=cache)
                    )
                )
                Subscription.objects.create(
                    member=member,
                    product=product,
                    period=growing_period,
                    quantity=1,
                    start_date=start_date,
                    end_date=growing_period.end_date,
                    mandate_ref=MandateReferenceProvider.get_or_create_mandate_reference(
                        member, cache=cache
                    ),
                    admin_confirmed=user_generator.get_confirmation_datetime(
                        start_date, cache=cache
                    ),
                    notice_period_duration=get_parameter_value(
                        ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD, cache=cache
                    ),
                    notice_period_unit=get_parameter_value(
                        ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT,
                        cache=cache,
                    ),
                )
                cls._start_association_membership(
                    member=member,
                    membership_type_name=cls.MEMBERSHIP_TYPE_ORDENTLICH,
                    start_date=start_date,
                    cache=cache,
                )
                cls._assign_random_payment_rhythm(
                    user_generator=user_generator, member=member, cache=cache
                )
                members_with_sizes.append((member, size))
                if random.random() < 0.3:
                    user_generator.generate_feedback_for_member(member)

        for _ in range(user_count - cls.NUMBER_OF_SHARE_MEMBERS):
            member = user_generator.create_member(
                parsed_user=parsed_users[member_index], cache=cache, fake=fake
            )
            member_index += 1
            cls._start_association_membership(
                member=member,
                membership_type_name=cls.MEMBERSHIP_TYPE_FOERDER,
                start_date=member.date_joined.date(),
                cache=cache,
            )
            cls._assign_random_payment_rhythm(
                user_generator=user_generator, member=member, cache=cache
            )

        cls.link_members_to_pickup_location(members_with_sizes)

        assign_member_numbers()
        # The creation date of subscriptions is used when generating payments, so we
        # have to set a realistic date.
        Subscription.objects.update(created_at=F("start_date"))

    @classmethod
    def _start_association_membership(
        cls, member: Member, membership_type_name: str, start_date, cache: dict
    ):
        AssociationMembershipChangeHandler.start_membership(
            member=member,
            association_membership_type=AssociationMembershipType.objects.get(
                name=membership_type_name
            ),
            start_date=start_date,
            actor=None,
            cache=cache,
        )

    @classmethod
    def _assign_random_payment_rhythm(cls, user_generator, member: Member, cache: dict):
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            rhythm=random.choice(MemberPaymentRhythm.Rhythm.choices)[0],
            valid_from=user_generator.get_random_date_in_range_biased_towards_lower_end(
                lower_boundary=member.date_joined.date(),
                upper_boundary=get_today(cache=cache),
            ),
            cache=cache,
            actor=member,
        )

    @classmethod
    def link_members_to_pickup_location(cls, members_with_sizes):
        city_locations, land_locations = cls.get_pickup_location_groups()
        assignment = cls.distribute_entries_by_city_land(
            weighted_entries=members_with_sizes,
            city_locations=city_locations,
            land_locations=land_locations,
        )
        MemberPickupLocation.objects.bulk_create(
            [
                MemberPickupLocation(
                    member=member,
                    pickup_location=pickup_location,
                    valid_from=member.date_joined.date(),
                )
                for member, pickup_location in assignment.items()
            ]
        )

    @classmethod
    def assign_bidder_pickup_locations(cls, bidder_assignments, pickup_locations):
        """
        Distribute the bids over the city/land depot groups so that about 62 % of the
        bid share units land in the city depots and about 38 % in the land depots,
        proportionally to the depot capacities within each group. Returns a
        ``{index: pickup_location}`` mapping or ``None`` if the city/land depot groups
        are not available (the caller then uses its generic assignment).
        """
        if not pickup_locations:
            return None

        city_locations, land_locations = cls.get_pickup_location_groups()
        if not city_locations or not land_locations:
            return None

        weighted_entries = [
            (index, size) for index, (_, _, _, size, _) in enumerate(bidder_assignments)
        ]
        return cls.distribute_entries_by_city_land(
            weighted_entries=weighted_entries,
            city_locations=city_locations,
            land_locations=land_locations,
        )
