import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.deliveries.services.pick_list_builder import PickListBuilder
from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.subscription_delivered_in_week_checked import (
    SubscriptionDeliveredInWeekChecker,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import PickupLocation, Member, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_product_price


class PickupLocationColumnProvider:
    @classmethod
    def get_pickup_location_columns(cls):
        return [
            ExportSegmentColumn(
                id="pickup_location_name",
                display_name="Name",
                description="",
                get_value=cls.get_value_pickup_location_name,
            ),
            ExportSegmentColumn(
                id="pickup_location_number_of_member",
                display_name="Anzahl an Mitglieder",
                description="Anzahl an Mitglieder die an diese Abholstation abholen",
                get_value=cls.get_value_pickup_location_number_of_member,
            ),
            ExportSegmentColumn(
                id="pickup_location_member_ids",
                display_name="Nummer der Mitglieder die an diese Abholstation abholen",
                description="Nummer der Mitglieder die an diese Abholstation abholen",
                get_value=cls.get_value_pickup_location_member_ids,
            ),
            ExportSegmentColumn(
                id="pickup_location_deliveries_current_week",
                display_name="Kommissionierliste",
                description="Alle Verträge die diese Woche geliefert werden",
                get_value=cls.get_value_pickup_location_deliveries_current_week,
            ),
        ]

    @classmethod
    def get_value_pickup_location_name(cls, location: PickupLocation, _, __):
        return location.name

    @classmethod
    def get_value_pickup_location_deliveries_current_week(
        cls,
        location: PickupLocation,
        reference_datetime: datetime.datetime,
        cache: dict,
    ):
        subscriptions = []
        for product_type in TapirCache.get_all_product_types(cache=cache):
            if not DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type, date=reference_datetime.date(), cache=cache
            ):
                continue

            subscriptions.extend(
                PickListBuilder.get_subscriptions_grouped_by_pickup_location_name(
                    delivery_date=reference_datetime.date(),
                    cache=cache,
                    product_type=product_type,
                ).get(location.name, [])
            )

        subscription_ids = [
            subscription.id
            for subscription in subscriptions
            if SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
                subscription=subscription,
                delivery_date=reference_datetime.date(),
                cache=cache,
                skip_donation_check=get_parameter_value(
                    key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
                    cache=cache,
                )
                == location.id,
            )
        ]

        subscriptions = Subscription.objects.filter(
            id__in=subscription_ids
        ).select_related("member", "product__type")

        subscriptions = sorted(
            subscriptions,
            key=lambda subscription: (
                subscription.member.last_name,
                subscription.member.first_name,
                -get_product_price(
                    product=subscription.product_id,
                    reference_date=reference_datetime.date(),
                    cache=cache,
                ).price,
            ),
        )

        return [
            {
                "member_no": subscription.member.member_no,
                "last_name": subscription.member.last_name,
                "first_name": subscription.member.first_name,
                "phone_number": subscription.member.phone_number,
                "email": subscription.member.email,
                "product_type_name": subscription.product.type.name,
                "product_name": subscription.product.name,
                "quantity": subscription.quantity,
            }
            for subscription in subscriptions
        ]

    @classmethod
    def get_value_pickup_location_number_of_member(
        cls, location: PickupLocation, reference_datetime: datetime.datetime, _
    ):

        members_annotated_with_pickup_location = MemberPickupLocationGetter.annotate_member_queryset_with_pickup_location_id_at_date(
            Member.objects.all(), reference_datetime.date()
        )

        return str(
            members_annotated_with_pickup_location.filter(
                current_pickup_location_id=location.id
            ).count()
        )

    @classmethod
    def get_value_pickup_location_member_ids(
        cls, location: PickupLocation, reference_datetime: datetime.datetime, _
    ):

        members_annotated_with_pickup_location = MemberPickupLocationGetter.annotate_member_queryset_with_pickup_location_id_at_date(
            Member.objects.all(), reference_datetime.date()
        )

        return "-".join(
            [
                str(member.member_no) or "Nicht mitglied"
                for member in members_annotated_with_pickup_location.filter(
                    current_pickup_location_id=location.id
                )
            ]
        )
