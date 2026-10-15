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
from apps.commissioning.viewsets.choices_models_viewsets import (
    SharesDeliveryDayViewSet,
)
from apps.commissioning.viewsets.delivery_viewsets import (
    DeliveryStationDayViewSet,
    DeliveryStationViewSet,
)
from apps.commissioning.viewsets.imports_viewsets import ExternalCodeMappingViewSet
from apps.commissioning.viewsets.shares_viewsets import (
    ShareTypeVariationViewSet,
    ShareTypeViewSet,
)
from django.utils import timezone

from tapir.deliveries.services.pick_list_builder import PickListBuilder
from tapir.jasmin_integration.exceptions import JasminSynchronisationException
from tapir.jasmin_integration.jasmin_api_client import JasminApiClient
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

__all__ = ["JasminSynchronisationService", "JasminSynchronisationException"]


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

    NUMBER_OF_DELIVERIES_TO_SYNCHRONISE = 6

    @classmethod
    def synchronise_everything(cls, user) -> list[str]:
        """Writes go through Jasmin's API as the given user, see JasminApiClient.

        Returns warnings about deliveries that couldn't be transferred."""
        cache = {}
        api = JasminApiClient(user=user)
        # Objects that don't exist in Tapir anymore stop being valid from the week
        # of the next delivery on, or later if Jasmin doesn't allow changes to that
        # week anymore.
        changes_monday = cls.get_first_changeable_monday(
            get_monday(get_next_delivery_date(cache=cache))
        )

        cls.synchronise_pickup_locations(api)
        cls.synchronise_product_types(api, changes_monday=changes_monday)
        cls.synchronise_products(api, changes_monday=changes_monday)
        return cls.synchronize_deliveries(api, cache=cache)

    @staticmethod
    def get_first_changeable_monday(week_monday: datetime.date) -> datetime.date:
        """Jasmin refuses validity periods that start in the past: changes to a week
        that already began only apply from the next week on. Jasmin compares with
        its own notion of today, so this does too."""
        today = timezone.now().date()
        first_monday_not_in_the_past = get_monday(today)
        if first_monday_not_in_the_past < today:
            first_monday_not_in_the_past += datetime.timedelta(days=7)
        return max(week_monday, first_monday_not_in_the_past)

    @classmethod
    def synchronise_pickup_locations(cls, api: JasminApiClient):
        # Stations are deactivated instead of deleted: the station days and demand
        # of past weeks still reference them. Their station days get closed in
        # synchronise_delivery_station_days.
        tapir_names = set(PickupLocation.objects.values_list("name", flat=True))
        jasmin_stations_by_name = {
            station.short_name: station
            for station in DeliveryStation.objects.order_by("is_active")
        }

        for name in tapir_names:
            station = jasmin_stations_by_name.get(name)
            if station is None:
                api.create(DeliveryStationViewSet, {"short_name": name})
            elif not station.is_active:
                api.update(DeliveryStationViewSet, station.id, {"is_active": True})

        for name, station in jasmin_stations_by_name.items():
            if name not in tapir_names and station.is_active:
                api.update(DeliveryStationViewSet, station.id, {"is_active": False})

    @classmethod
    def synchronise_time_bound_objects(
        cls,
        api: JasminApiClient,
        viewset_class,
        tapir_keys: set,
        jasmin_objects_by_key: dict,
        changes_monday: datetime.date,
    ) -> set:
        """Reopens the Jasmin objects whose key is back in Tapir, ends the validity
        of the ones whose key isn't in Tapir anymore.

        Returns the keys for which a Jasmin object must be created."""
        keys_to_create = set()
        for key in tapir_keys:
            jasmin_object = jasmin_objects_by_key.get(key)
            if jasmin_object is None:
                keys_to_create.add(key)
            elif jasmin_object.valid_until is not None:
                # Reopening instead of creating a new object: Jasmin refuses
                # overlapping validity periods for the same share type or size.
                api.update(viewset_class, jasmin_object.id, {"valid_until": None})

        for key, jasmin_object in jasmin_objects_by_key.items():
            if key not in tapir_keys and jasmin_object.valid_until is None:
                cls.end_validity(api, viewset_class, jasmin_object, changes_monday)

        return keys_to_create

    @classmethod
    def end_validity(
        cls,
        api: JasminApiClient,
        viewset_class,
        time_bound_object,
        changes_monday: datetime.date,
    ):
        """Makes the object valid until the sunday before the given week.

        Validity periods can't end before they start: an object that starts on or
        after the given week gets deleted, or if Jasmin refuses the deletion
        (because demand rows reference it for example), stays valid until the end of
        its first week."""
        if time_bound_object.valid_from < changes_monday:
            api.update(
                viewset_class,
                time_bound_object.id,
                {"valid_until": changes_monday - datetime.timedelta(days=1)},
            )
            return

        try:
            api.destroy(viewset_class, time_bound_object.id)
        except JasminSynchronisationException:
            api.update(
                viewset_class,
                time_bound_object.id,
                {
                    "valid_until": time_bound_object.valid_from
                    + datetime.timedelta(days=6)
                },
            )

    @classmethod
    def synchronise_product_types(
        cls, api: JasminApiClient, changes_monday: datetime.date
    ):
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
            api=api,
            viewset_class=ShareTypeViewSet,
            tapir_keys=set(tapir_product_types_by_name.keys()),
            jasmin_objects_by_key=jasmin_product_types_by_name,
            changes_monday=changes_monday,
        )
        for name in sorted(names_to_create):
            api.create(
                ShareTypeViewSet,
                cls.build_jasmin_product_type_data(tapir_product_types_by_name[name]),
            )

    @classmethod
    def build_jasmin_product_type_data(cls, tapir_product_type: ProductType) -> dict:
        return {
            "name": tapir_product_type.name,
            "short_name": tapir_product_type.name,
            "delivery_cycle": cls.get_jasmin_delivery_cycle(
                tapir_product_type.delivery_cycle
            ),
            "valid_from": get_monday(tapir_product_type.created_at.date()),
            "share_option": cls.get_jasmin_share_option(tapir_product_type.name),
        }

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
    def synchronise_products(cls, api: JasminApiClient, changes_monday: datetime.date):
        # Product names are only unique within a product type ("M" can exist in
        # several types), so products are identified by their type's name and their
        # own name. In Jasmin: the share type's name and the variation's description.
        tapir_product_by_key = {
            (product.type.name, product.name): product
            for product in Product.objects.select_related("type").exclude(
                type__delivery_cycle=NO_DELIVERY[0]
            )
        }
        # Ordered by validity so that the most recent object wins for each key
        jasmin_product_by_key = {
            (product.share_type.name, product.description): product
            for product in ShareTypeVariation.objects.select_related(
                "share_type"
            ).order_by("valid_from")
        }

        keys_to_create = cls.synchronise_time_bound_objects(
            api=api,
            viewset_class=ShareTypeVariationViewSet,
            tapir_keys=set(tapir_product_by_key.keys()),
            jasmin_objects_by_key=jasmin_product_by_key,
            changes_monday=changes_monday,
        )
        for key in sorted(keys_to_create):
            api.create(
                ShareTypeVariationViewSet,
                cls.build_jasmin_product_data(tapir_product_by_key[key]),
            )

    @staticmethod
    def get_variation_code(product_type_name: str, product_name: str) -> str:
        """How the deliveries CSV references a product, see synchronise_products."""
        return f"{product_type_name} / {product_name}"

    @classmethod
    def build_jasmin_product_data(cls, tapir_product: Product) -> dict:
        return {
            "share_type": ShareType.objects.filter(name=tapir_product.type.name)
            .latest("valid_from")
            .id,
            "variation_type": ShareTypeVariation.VariationType.PHYSICAL,
            "size": cls.get_jasmin_size(tapir_product.name),
            "valid_from": get_monday(tapir_product.created_at.date()),
            "description": tapir_product.name,
        }

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
    def synchronize_deliveries(cls, api: JasminApiClient, cache: dict) -> list[str]:
        warnings = []
        delivery_date = get_next_delivery_date(cache=cache)
        for _ in range(cls.NUMBER_OF_DELIVERIES_TO_SYNCHRONISE):
            warnings.extend(
                cls.synchronize_delivery(api, delivery_date=delivery_date, cache=cache)
            )
            delivery_date = get_next_delivery_date(
                reference_date=delivery_date + datetime.timedelta(days=1),
                cache=cache,
            )

        return warnings

    @classmethod
    def synchronize_delivery(
        cls, api: JasminApiClient, delivery_date: datetime.date, cache: dict
    ) -> list[str]:
        year, delivery_week, _ = delivery_date.isocalendar()
        week_monday = get_monday(delivery_date)

        cls.synchronise_delivery_station_days(
            api, delivery_date=delivery_date, cache=cache
        )
        cls.synchronise_code_mappings(api, week_monday)
        rows, warnings = cls.build_delivery_rows(
            delivery_date=delivery_date, cache=cache
        )

        original_filename = f"tapir_deliveries_{year}_KW{delivery_week}.csv"
        try:
            batch = ShareImportService.ingest_upload(
                file_bytes=cls.build_deliveries_csv(rows),
                original_filename=original_filename,
                year=year,
                delivery_week=delivery_week,
                uploaded_by=api.user,
            )
        except ShareImportFileAlreadyUsed as error:
            if error.details["status"] == ShareImportBatch.STATUS_APPLIED:
                # The demand currently applied for that week is already up-to-date.
                return warnings

            # The same file was applied before but has been superseded by another one
            # since then (for example a joker that got taken then cancelled).
            # Jasmin refuses the same file twice, the note makes the file unique.
            batch = ShareImportService.ingest_upload(
                file_bytes=cls.build_deliveries_csv(
                    rows, note=f"Tapir-Sync {get_now(cache=cache).isoformat()}"
                ),
                original_filename=original_filename,
                year=year,
                delivery_week=delivery_week,
                uploaded_by=api.user,
            )

        cls.apply_batch(batch, user=api.user)
        return warnings

    @classmethod
    def apply_batch(cls, batch: ShareImportBatch, user) -> ShareImportBatch:
        outcome = ShareImportService.parse_and_validate(batch)
        if not outcome.is_ok:
            raise JasminSynchronisationException(
                f"Die Lieferungen für KW{batch.delivery_week} {batch.year} konnten "
                f"nicht importiert werden: {outcome.errors}"
            )

        ShareImportService.build_preview(batch, outcome.rows)
        return ShareImportService.apply(batch, outcome.rows, applied_by=user)

    @classmethod
    def synchronise_delivery_station_days(
        cls, api: JasminApiClient, delivery_date: datetime.date, cache: dict
    ):
        # Station days are valid for whole ISO weeks, starting on a monday.
        week_monday = get_monday(delivery_date)
        changes_monday = cls.get_first_changeable_monday(week_monday)

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

            shares_delivery_day_id = cls.get_or_create_shares_delivery_day_id(
                api, day_number=day_number, week_monday=week_monday
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
                (station_id_by_name[pickup_location.name], shares_delivery_day_id)
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
            cls.end_validity(
                api, DeliveryStationDayViewSet, station_day, changes_monday
            )

        for (
            station_id,
            day_id,
        ), wanted_fields in wanted_fields_by_station_and_day_id.items():
            station_day = existing_station_days_by_station_and_day_id.get(
                (station_id, day_id)
            )
            if station_day is None:
                if day_id is None:
                    # The delivery day itself only starts after this week
                    continue
                if cls.station_day_exists_later(station_id, day_id, week_monday):
                    # Created while synchronising an earlier week, starting with
                    # the first week Jasmin still allows changes for.
                    continue
                api.create(
                    DeliveryStationDayViewSet,
                    {
                        "delivery_station": station_id,
                        "delivery_day": day_id,
                        "valid_from": changes_monday,
                        **wanted_fields,
                    },
                )
                continue

            if all(
                getattr(station_day, field) == value
                for field, value in wanted_fields.items()
            ):
                continue
            api.update(DeliveryStationDayViewSet, station_day.id, wanted_fields)

    @staticmethod
    def station_day_exists_later(
        station_id: str, day_id: str, week_monday: datetime.date
    ) -> bool:
        return DeliveryStationDay.objects.filter(
            delivery_station_id=station_id,
            delivery_day_id=day_id,
            valid_from__gt=week_monday,
        ).exists()

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
    def get_or_create_shares_delivery_day_id(
        cls, api: JasminApiClient, day_number: int, week_monday: datetime.date
    ) -> str | None:
        """The delivery day valid in the given week, created if there is none.

        Returns None if the delivery day only starts after the given week: Jasmin
        refuses to create one starting in a week that already began."""
        shares_delivery_day = SharesDeliveryDay.objects.filter(
            active_on_date_q(week_monday), day_number=day_number
        ).first()
        if shares_delivery_day is not None:
            return shares_delivery_day.id

        if SharesDeliveryDay.objects.filter(
            day_number=day_number, valid_from__gt=week_monday
        ).exists():
            # Created while synchronising an earlier week, starting with the first
            # week Jasmin still allows changes for.
            return None

        valid_from = cls.get_first_changeable_monday(week_monday)
        shares_delivery_day_id = api.create(
            SharesDeliveryDayViewSet,
            {"day_number": day_number, "valid_from": valid_from},
        )["id"]
        return shares_delivery_day_id if valid_from == week_monday else None

    @classmethod
    def build_deliveries_csv(cls, rows: list[dict], note: str | None = None) -> bytes:
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
        for row in rows:
            writer.writerow({**row, **({"note": note} if note is not None else {})})

        return output.getvalue().encode("utf-8")

    @classmethod
    def build_delivery_rows(
        cls, delivery_date: datetime.date, cache: dict
    ) -> tuple[list[dict], list[str]]:
        """The rows of the deliveries CSV, and warnings about the deliveries left out
        because their station day or product doesn't exist in Jasmin in that week."""
        year, delivery_week, _ = delivery_date.isocalendar()
        week_monday = get_monday(delivery_date)
        pickup_location_id_by_name = dict(
            PickupLocation.objects.values_list("name", "id")
        )
        jasmin_station_days = set(
            DeliveryStationDay.objects.filter(
                active_on_date_q(week_monday), delivery_station__is_active=True
            ).values_list("delivery_station__short_name", "delivery_day__day_number")
        )
        jasmin_variation_codes = {
            cls.get_variation_code(share_type_name, description)
            for share_type_name, description in ShareTypeVariation.objects.filter(
                active_on_date_q(week_monday)
            ).values_list("share_type__name", "description")
        }

        rows = []
        left_out_quantity_by_pickup_location_name = {}
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
                    variation_code = cls.get_variation_code(
                        product_type.name, product_name
                    )
                    if (
                        pickup_location_name,
                        delivery_day,
                    ) not in jasmin_station_days or (
                        variation_code not in jasmin_variation_codes
                    ):
                        left_out_quantity_by_pickup_location_name[
                            pickup_location_name
                        ] = (
                            left_out_quantity_by_pickup_location_name.get(
                                pickup_location_name, 0
                            )
                            + quantity
                        )
                        continue

                    rows.append(
                        {
                            "year": year,
                            "delivery_week": delivery_week,
                            "delivery_station_code": pickup_location_name,
                            "delivery_day_code": delivery_day,
                            "variation_code": variation_code,
                            "quantity": quantity,
                        }
                    )

        warnings = [
            f"KW{delivery_week} {year}: {quantity} Anteil(e) für {pickup_location_name} "
            f"nicht übertragen, der Verteilort oder das Produkt existiert in Jasmin "
            f"erst ab einer späteren Woche."
            for pickup_location_name, quantity in sorted(
                left_out_quantity_by_pickup_location_name.items()
            )
        ]
        return rows, warnings

    @classmethod
    def synchronise_code_mappings(
        cls, api: JasminApiClient, reference_date: datetime.date
    ):
        # The deliveries CSV references stations by name, variations by product type
        # and product name (see get_variation_code) and days by day number (0=Monday
        # in both Tapir and Jasmin).
        internal_id_by_code_by_kind = {
            ExternalCodeMapping.KIND_STATION: {
                short_name: str(station_id)
                for station_id, short_name in DeliveryStation.objects.filter(
                    is_active=True
                ).values_list("id", "short_name")
            },
            ExternalCodeMapping.KIND_VARIATION: {
                cls.get_variation_code(share_type_name, description): str(variation_id)
                for variation_id, share_type_name, description in (
                    ShareTypeVariation.objects.filter(
                        active_on_date_q(reference_date)
                    ).values_list("id", "share_type__name", "description")
                )
            },
            ExternalCodeMapping.KIND_DAY: {
                str(day_number): str(day_id)
                for day_id, day_number in SharesDeliveryDay.objects.filter(
                    active_on_date_q(reference_date)
                ).values_list("id", "day_number")
            },
        }

        existing_mappings = {
            (mapping.kind, mapping.external_code): mapping
            for mapping in ExternalCodeMapping.objects.all()
        }
        for kind, internal_id_by_code in internal_id_by_code_by_kind.items():
            for code, internal_id in internal_id_by_code.items():
                mapping = existing_mappings.get((kind, code))
                if mapping is None:
                    api.create(
                        ExternalCodeMappingViewSet,
                        {
                            "kind": kind,
                            "external_code": code,
                            "internal_id": internal_id,
                        },
                    )
                elif mapping.internal_id != internal_id:
                    api.update(
                        ExternalCodeMappingViewSet,
                        mapping.id,
                        {"internal_id": internal_id},
                    )
