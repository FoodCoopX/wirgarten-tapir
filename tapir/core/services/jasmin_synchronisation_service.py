import csv
import datetime
import io

from apps.commissioning.errors import ShareImportFileAlreadyUsed
from apps.commissioning.models import (
    DeliveryStation,
    DeliveryStationDay,
    ExternalCodeMapping,
    ShareImportBatch,
    SharesDeliveryDay,
    ShareType,
    ShareTypeVariation,
)
from apps.commissioning.models.choices import (
    DeliveryCycleOptions,
    ShareOptions,
    ShareTypeVariationSizeOptions,
)
from apps.commissioning.models.managers import active_on_date_q
from apps.commissioning.services import ShareImportService
from django.db import transaction
from django.db.models import ProtectedError, RestrictedError

from tapir.deliveries.services.pick_list_builder import PickListBuilder
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import (
    NO_DELIVERY,
    WEEKLY,
    ODD_WEEKS,
    EVEN_WEEKS,
    EVERY_FOUR_WEEKS,
)
from tapir.wirgarten.models import (
    LocationRoute,
    PickupLocation,
    PickupLocationOpeningTime,
    ProductType,
    Product,
)
from tapir.wirgarten.service.get_next_delivery_date import get_next_delivery_date
from tapir.wirgarten.utils import get_now


class JasminSynchronisationException(Exception):
    def __init__(self, message: str, *args):
        self.message = message
        super().__init__(message, *args)


class JasminSynchronisationService:
    TAPIR_TO_JASMIN_DELIVERY_CYCLE_MAP = {
        WEEKLY[0]: DeliveryCycleOptions.WEEKLY,
        ODD_WEEKS[0]: DeliveryCycleOptions.ODD_WEEKS,
        EVEN_WEEKS[0]: DeliveryCycleOptions.EVEN_WEEKS,
        EVERY_FOUR_WEEKS[0]: DeliveryCycleOptions.ALL_FOUR_WEEKS,
    }

    KEYWORD_TO_JASMIN_SHARE_OPTION_MAP = {
        "ernte": ShareOptions.HARVEST_SHARE,
        "obst": ShareOptions.HARVEST_SHARE_FRUITS_ONLY,
        "hühn": ShareOptions.CHICKEN_SHARE,
        "eier": ShareOptions.CHICKEN_SHARE,
    }

    KEYWORD_TO_JASMIN_SIZE_MAP = {
        "klein": ShareTypeVariationSizeOptions.S,
        "mittel": ShareTypeVariationSizeOptions.M,
        "normal": ShareTypeVariationSizeOptions.M,
        "standard": ShareTypeVariationSizeOptions.M,
        "groß": ShareTypeVariationSizeOptions.L,
        "ganz": ShareTypeVariationSizeOptions.FULL,
        "halb": ShareTypeVariationSizeOptions.HALF,
    }

    NUMBER_OF_DELIVERIES_TO_SYNCHRONISE = 4

    @classmethod
    def synchronise_everything(cls):
        cache = {}
        # Objects that don't exist in Tapir anymore stop being valid from the week
        # of the next delivery on.
        week_monday = get_monday(get_next_delivery_date(cache=cache))

        cls.synchronise_pickup_locations()
        cls.synchronise_product_types(week_monday=week_monday)
        cls.synchronise_products(week_monday=week_monday)
        cls.synchronize_deliveries(cache=cache)

    @classmethod
    def synchronise_pickup_locations(cls):
        # Stations are deactivated instead of deleted: the station days and demand
        # of past weeks still reference them. Their station days get closed in
        # synchronise_delivery_station_days.
        tapir_names = set(PickupLocation.objects.values_list("name", flat=True))
        jasmin_stations_by_name = {
            station.short_name: station
            for station in DeliveryStation.objects.order_by("is_active")
        }

        location_names_to_create = []
        for name in tapir_names:
            station = jasmin_stations_by_name.get(name)
            if station is None:
                location_names_to_create.append(name)
            elif not station.is_active:
                station.is_active = True
                station.save()

        for name, station in jasmin_stations_by_name.items():
            if name not in tapir_names and station.is_active:
                station.is_active = False
                station.save()

        if len(location_names_to_create) > 0:
            DeliveryStation.objects.bulk_create(
                [DeliveryStation(short_name=name) for name in location_names_to_create]
            )

    @classmethod
    def synchronise_time_bound_objects(
        cls,
        tapir_names: set[str],
        jasmin_objects_by_name: dict,
        week_monday: datetime.date,
    ) -> set[str]:
        """Reopens the Jasmin objects whose name is back in Tapir, ends the validity
        of the ones whose name isn't in Tapir anymore.

        Returns the names for which a Jasmin object must be created."""
        names_to_create = set()
        for name in tapir_names:
            jasmin_object = jasmin_objects_by_name.get(name)
            if jasmin_object is None:
                names_to_create.add(name)
            elif jasmin_object.valid_until is not None:
                # Reopening instead of creating a new object: Jasmin refuses
                # overlapping validity periods for the same share type or size.
                jasmin_object.valid_until = None
                jasmin_object.save()

        for name, jasmin_object in jasmin_objects_by_name.items():
            if name not in tapir_names and jasmin_object.valid_until is None:
                cls.end_validity(jasmin_object, week_monday)

        return names_to_create

    @classmethod
    def end_validity(cls, time_bound_object, week_monday: datetime.date):
        """Makes the object valid until the sunday before the given week.

        Validity periods can't end before they start: an object that starts on or
        after the given week gets deleted, or if it is referenced (by demand rows
        for example), stays valid until the end of its first week."""
        if time_bound_object.valid_from < week_monday:
            time_bound_object.valid_until = week_monday - datetime.timedelta(days=1)
            time_bound_object.save()
            return

        try:
            with transaction.atomic():
                time_bound_object.delete()
        except (ProtectedError, RestrictedError):
            time_bound_object.valid_until = (
                time_bound_object.valid_from + datetime.timedelta(days=6)
            )
            time_bound_object.save()

    @classmethod
    def synchronise_product_types(cls, week_monday: datetime.date):
        tapir_product_types_by_name = {
            product_type.name: product_type
            for product_type in ProductType.objects.exclude(
                delivery_cycle=NO_DELIVERY[0]
            )
        }
        # Ordered by validity so that the most recent object wins for each name
        jasmin_product_types_by_name = {
            product_type.name: product_type
            for product_type in ShareType.objects.order_by("valid_from")
        }

        names_to_create = cls.synchronise_time_bound_objects(
            tapir_names=set(tapir_product_types_by_name.keys()),
            jasmin_objects_by_name=jasmin_product_types_by_name,
            week_monday=week_monday,
        )
        if len(names_to_create) > 0:
            jasmin_product_types_to_create = []
            for name in names_to_create:
                tapir_product_type = tapir_product_types_by_name[name]
                jasmin_product_types_to_create.append(
                    cls.build_jasmin_product_type(tapir_product_type)
                )

            ShareType.objects.bulk_create(jasmin_product_types_to_create)

    @classmethod
    def build_jasmin_product_type(cls, tapir_product_type: ProductType) -> ShareType:
        return ShareType(
            name=tapir_product_type.name,
            short_name=tapir_product_type.name,
            delivery_cycle=cls.get_jasmin_delivery_cycle(
                tapir_product_type.delivery_cycle
            ),
            valid_from=get_monday(tapir_product_type.created_at.date()),
            share_option=cls.get_jasmin_share_option(tapir_product_type.name),
        )

    @classmethod
    def get_jasmin_delivery_cycle(cls, tapir_delivery_cycle: str):
        if tapir_delivery_cycle not in cls.TAPIR_TO_JASMIN_DELIVERY_CYCLE_MAP:
            raise JasminSynchronisationException(
                f"Folgende Lieferzyklus wird von Jasmin nicht unterstützt: {tapir_delivery_cycle}"
            )

        return cls.TAPIR_TO_JASMIN_DELIVERY_CYCLE_MAP[tapir_delivery_cycle]

    @classmethod
    def get_jasmin_share_option(cls, product_type_name: str):
        for keyword, share_option in cls.KEYWORD_TO_JASMIN_SHARE_OPTION_MAP.items():
            if keyword.casefold() in product_type_name.casefold():
                return share_option

        # Harvest share as default so that the share type is shown on the frontend
        return ShareOptions.HARVEST_SHARE

    @classmethod
    def synchronise_products(cls, week_monday: datetime.date):
        tapir_product_by_name = {
            product.name: product
            for product in Product.objects.select_related("type").exclude(
                type__delivery_cycle=NO_DELIVERY[0]
            )
        }
        # Ordered by validity so that the most recent object wins for each name
        jasmin_product_by_name = {
            product.description: product
            for product in ShareTypeVariation.objects.order_by("valid_from")
        }

        names_to_create = cls.synchronise_time_bound_objects(
            tapir_names=set(tapir_product_by_name.keys()),
            jasmin_objects_by_name=jasmin_product_by_name,
            week_monday=week_monday,
        )
        if len(names_to_create) > 0:
            jasmin_product_to_create = []
            for name in names_to_create:
                tapir_product = tapir_product_by_name[name]
                jasmin_product_to_create.append(cls.build_jasmin_product(tapir_product))

            ShareTypeVariation.objects.bulk_create(jasmin_product_to_create)

    @classmethod
    def build_jasmin_product(cls, tapir_product: Product):
        return ShareTypeVariation(
            share_type=ShareType.objects.filter(name=tapir_product.type.name).latest(
                "valid_from"
            ),
            variation_type=ShareTypeVariation.VariationType.PHYSICAL,
            size=cls.get_jasmin_size(tapir_product.name),
            valid_from=get_monday(tapir_product.created_at.date()),
            description=tapir_product.name,
        )

    @classmethod
    def get_jasmin_size(cls, product_name: str):
        for size in ShareTypeVariationSizeOptions:
            if size.value.casefold() == product_name.casefold():
                return size

        for keyword, size in cls.KEYWORD_TO_JASMIN_SIZE_MAP.items():
            if keyword.casefold() in product_name.casefold():
                return size

        raise JasminSynchronisationException(
            f"Folgende Produktgröße wird von Jasmin nicht unterstützt: {product_name}"
        )

    @classmethod
    def synchronize_deliveries(cls, cache: dict | None = None):
        if cache is None:
            cache = {}

        batches = []
        delivery_date = get_next_delivery_date(cache=cache)
        for _ in range(cls.NUMBER_OF_DELIVERIES_TO_SYNCHRONISE):
            batches.append(
                cls.synchronize_delivery(delivery_date=delivery_date, cache=cache)
            )
            delivery_date = get_next_delivery_date(
                reference_date=delivery_date + datetime.timedelta(days=1),
                cache=cache,
            )

        return batches

    @classmethod
    def synchronize_delivery(cls, delivery_date: datetime.date, cache: dict):
        year, delivery_week, _ = delivery_date.isocalendar()

        cls.synchronise_delivery_station_days(delivery_date=delivery_date, cache=cache)
        cls.synchronise_code_mappings(get_monday(delivery_date))

        original_filename = f"tapir_deliveries_{year}_KW{delivery_week}.csv"
        try:
            batch = ShareImportService.ingest_upload(
                file_bytes=cls.build_deliveries_csv(
                    delivery_date=delivery_date, cache=cache
                ),
                original_filename=original_filename,
                year=year,
                delivery_week=delivery_week,
                uploaded_by=None,
            )
        except ShareImportFileAlreadyUsed as error:
            if error.details["status"] == ShareImportBatch.STATUS_APPLIED:
                # The demand currently applied for that week is already up-to-date.
                return ShareImportBatch.objects.get(id=error.details["batch_id"])

            # The same file was applied before but has been superseded by another one
            # since then (for example a joker that got taken then cancelled).
            # Jasmin refuses the same file twice, the note makes the file unique.
            batch = ShareImportService.ingest_upload(
                file_bytes=cls.build_deliveries_csv(
                    delivery_date=delivery_date,
                    cache=cache,
                    note=f"Tapir-Sync {get_now(cache=cache).isoformat()}",
                ),
                original_filename=original_filename,
                year=year,
                delivery_week=delivery_week,
                uploaded_by=None,
            )

        return cls.apply_batch(batch)

    @classmethod
    def apply_batch(cls, batch: ShareImportBatch) -> ShareImportBatch:
        outcome = ShareImportService.parse_and_validate(batch)
        if not outcome.is_ok:
            raise JasminSynchronisationException(
                f"Die Lieferungen für KW{batch.delivery_week} {batch.year} konnten "
                f"nicht importiert werden: {outcome.errors}"
            )

        ShareImportService.build_preview(batch, outcome.rows)
        return ShareImportService.apply(batch, outcome.rows, applied_by=None)

    @classmethod
    def synchronise_delivery_station_days(
        cls, delivery_date: datetime.date, cache: dict
    ):
        # Station days are valid for whole ISO weeks, starting on a monday.
        week_monday = get_monday(delivery_date)

        station_id_by_name = dict(
            DeliveryStation.objects.filter(is_active=True).values_list(
                "short_name", "id"
            )
        )
        tour_and_stop_order_by_pickup_location_id = (
            cls.get_tour_and_stop_order_by_pickup_location_id()
        )
        wanted_fields_by_station_and_day_id = {}
        for pickup_location in PickupLocation.objects.all():
            day_number = PickupLocationDeliveryDayService.get_delivery_day(
                pickup_location_id=pickup_location.id, cache=cache
            )
            if day_number is None:
                continue

            shares_delivery_day = cls.get_or_create_shares_delivery_day(
                day_number=day_number, week_monday=week_monday
            )
            opening_time = (
                PickupLocationOpeningTime.objects.filter(
                    pickup_location_id=pickup_location.id, day_of_week=day_number
                )
                .order_by("open_time")
                .first()
            )
            tour_number, stop_order = tour_and_stop_order_by_pickup_location_id[
                pickup_location.id
            ]
            wanted_fields_by_station_and_day_id[
                (station_id_by_name[pickup_location.name], shares_delivery_day.id)
            ] = {
                "pickup_time_begin": opening_time.open_time if opening_time else None,
                "pickup_time_end": opening_time.close_time if opening_time else None,
                "tour_number": tour_number,
                "stop_order": stop_order,
                # Reopens a station day that got closed while it was referenced
                "valid_until": None,
            }

        existing_station_days_by_station_and_day_id = {
            (station_day.delivery_station_id, station_day.delivery_day_id): station_day
            for station_day in DeliveryStationDay.objects.filter(
                active_on_date_q(week_monday)
            )
        }

        for key, station_day in existing_station_days_by_station_and_day_id.items():
            if (
                key in wanted_fields_by_station_and_day_id
                or station_day.valid_until is not None
            ):
                continue
            cls.end_validity(station_day, week_monday)

        for (
            station_id,
            day_id,
        ), wanted_fields in wanted_fields_by_station_and_day_id.items():
            station_day = existing_station_days_by_station_and_day_id.get(
                (station_id, day_id)
            )
            if station_day is None:
                DeliveryStationDay(
                    delivery_station_id=station_id,
                    delivery_day_id=day_id,
                    valid_from=week_monday,
                    **wanted_fields,
                ).save()
                continue

            if all(
                getattr(station_day, field) == value
                for field, value in wanted_fields.items()
            ):
                continue
            for field, value in wanted_fields.items():
                setattr(station_day, field, value)
            station_day.save()

    @classmethod
    def get_tour_and_stop_order_by_pickup_location_id(cls) -> dict:
        # Tapir doesn't store an order: like the location route exports, routes and
        # the pickup locations within them are sorted by name. Pickup locations
        # without a route are grouped in an extra tour after the last route.
        routes = list(LocationRoute.objects.order_by("name"))
        tour_number_by_route_id = {
            route.id: tour_number for tour_number, route in enumerate(routes, start=1)
        }
        tour_number_without_route = len(routes) + 1

        tour_and_stop_order_by_pickup_location_id = {}
        next_stop_order_by_tour_number = {}
        for pickup_location in PickupLocation.objects.order_by("name"):
            tour_number = tour_number_by_route_id.get(
                pickup_location.location_route_id, tour_number_without_route
            )
            stop_order = next_stop_order_by_tour_number.get(tour_number, 1)
            next_stop_order_by_tour_number[tour_number] = stop_order + 1
            tour_and_stop_order_by_pickup_location_id[pickup_location.id] = (
                tour_number,
                stop_order,
            )

        return tour_and_stop_order_by_pickup_location_id

    @classmethod
    def get_or_create_shares_delivery_day(
        cls, day_number: int, week_monday: datetime.date
    ) -> SharesDeliveryDay:
        shares_delivery_day = SharesDeliveryDay.objects.filter(
            active_on_date_q(week_monday), day_number=day_number
        ).first()
        if shares_delivery_day is not None:
            return shares_delivery_day

        shares_delivery_day = SharesDeliveryDay(
            day_number=day_number, valid_from=week_monday
        )
        shares_delivery_day.save()
        return shares_delivery_day

    @classmethod
    def build_deliveries_csv(
        cls, delivery_date: datetime.date, cache: dict, note: str | None = None
    ) -> bytes:
        year, delivery_week, _ = delivery_date.isocalendar()
        pickup_location_id_by_name = dict(
            PickupLocation.objects.values_list("name", "id")
        )

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "year",
                "delivery_week",
                "delivery_station_code",
                "delivery_day_code",
                "variation_code",
                "quantity",
                *(["note"] if note is not None else []),
            ],
        )
        writer.writeheader()

        for product_type in ProductType.objects.exclude(
            delivery_cycle=NO_DELIVERY[0]
        ).order_by("name"):
            subscriptions_by_pickup_location_name = (
                PickListBuilder.get_subscriptions_grouped_by_pickup_location_name(
                    delivery_date=delivery_date,
                    cache=cache,
                    product_type=product_type,
                )
            )
            for pickup_location_name in sorted(
                subscriptions_by_pickup_location_name.keys()
            ):
                subscriptions = PickListBuilder.get_delivered_subscriptions(
                    subscriptions=subscriptions_by_pickup_location_name[
                        pickup_location_name
                    ],
                    delivery_date=delivery_date,
                    cache=cache,
                )
                if len(subscriptions) == 0:
                    continue

                delivery_day = PickupLocationDeliveryDayService.get_delivery_day(
                    pickup_location_id=pickup_location_id_by_name[pickup_location_name],
                    cache=cache,
                )
                if delivery_day is None:
                    raise JasminSynchronisationException(
                        f"Folgender Verteilort hat keine Öffnungszeiten, "
                        f"der Liefertag kann nicht bestimmt werden: {pickup_location_name}"
                    )

                quantities_by_product_name = (
                    PickListBuilder.get_delivery_quantity_by_product_name(subscriptions)
                )
                for product_name, quantity in sorted(
                    quantities_by_product_name.items()
                ):
                    writer.writerow(
                        {
                            "year": year,
                            "delivery_week": delivery_week,
                            "delivery_station_code": pickup_location_name,
                            "delivery_day_code": delivery_day,
                            "variation_code": product_name,
                            "quantity": quantity,
                            **({"note": note} if note is not None else {}),
                        }
                    )

        return output.getvalue().encode("utf-8")

    @classmethod
    def synchronise_code_mappings(cls, reference_date: datetime.date):
        # The deliveries CSV references stations by name, variations by product name
        # and days by day number (0=Monday in both Tapir and Jasmin).
        internal_id_by_code_by_kind = {
            ExternalCodeMapping.KIND_STATION: {
                short_name: str(station_id)
                for station_id, short_name in DeliveryStation.objects.filter(
                    is_active=True
                ).values_list("id", "short_name")
            },
            ExternalCodeMapping.KIND_VARIATION: {
                description: str(variation_id)
                for variation_id, description in ShareTypeVariation.objects.filter(
                    active_on_date_q(reference_date)
                ).values_list("id", "description")
            },
            ExternalCodeMapping.KIND_DAY: {
                str(day_number): str(day_id)
                for day_id, day_number in SharesDeliveryDay.objects.filter(
                    active_on_date_q(reference_date)
                ).values_list("id", "day_number")
            },
        }

        for kind, internal_id_by_code in internal_id_by_code_by_kind.items():
            for code, internal_id in internal_id_by_code.items():
                ExternalCodeMapping.objects.update_or_create(
                    kind=kind,
                    external_code=code,
                    defaults={"internal_id": internal_id},
                )
