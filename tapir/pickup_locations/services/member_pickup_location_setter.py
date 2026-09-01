import datetime

from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.payments.services.month_payment_builder_delivery_charges import (
    MonthPaymentBuilderDeliveryCharges,
)
from tapir.pickup_locations.models import PickupLocationChangedLogEntry
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_opening_times_formatter import (
    PickupLocationOpeningTimesFormatter,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.services.tapir_cache_manager import TapirCacheManager
from tapir.utils.user_utils import UserUtils
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Member, MemberPickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today, format_date


class MemberPickupLocationSetter:
    @classmethod
    def link_member_to_pickup_location(
        cls,
        pickup_location_id: str | None,
        member: Member,
        valid_from: datetime.date,
        actor: TapirUser | None,
        cache: dict,
    ):
        old_pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
            member=member, reference_date=valid_from, cache=cache
        )
        if old_pickup_location is None:
            valid_from = min(valid_from, get_today(cache=cache))

        MemberPickupLocation.objects.filter(
            member=member, valid_from__gte=valid_from
        ).delete()
        member_pickup_location = MemberPickupLocation.objects.create(
            member_id=member.id,
            pickup_location_id=pickup_location_id,
            valid_from=valid_from,
        )

        TapirCacheManager.clear_category(
            cache=cache, category=TapirCacheManager.CATEGORY_MEMBER_PICKUP_LOCATIONS
        )

        PickupLocationChangedLogEntry().populate_pickup_location(
            actor=actor,
            member_pickup_location=member_pickup_location,
            old_pickup_location=old_pickup_location,
            user=member,
        ).save()

        if old_pickup_location is not None and pickup_location_id is not None:
            if get_parameter_value(
                key=ParameterKeys.DELIVERY_CHARGE_PER_PICKUP_LOCATION_ENABLED,
                cache=cache,
            ):
                # Refund any delivery charge the member prepaid for the location they
                # are leaving but will no longer use this period. Done here, once per
                # switch, rather than as a negative payment in the daily billing run.
                refund_credits = MonthPaymentBuilderDeliveryCharges.build_refund_credits_for_pickup_location_change(
                    member=member, reference_date=valid_from, cache=cache
                )
                MemberCreditCreator.save_credits_with_log_entries(
                    refund_credits, actor=actor
                )

            pickup_location = TapirCache.get_pickup_location_by_id(
                cache=cache, pickup_location_id=pickup_location_id
            )

            TransactionalTrigger.fire_action(
                TransactionalTriggerData(
                    key=Events.MEMBERAREA_CHANGE_PICKUP_LOCATION,
                    recipient_id_in_base_queryset=member.id,
                    token_data={
                        "pickup_location": pickup_location.name,
                        "pickup_location_start_date": format_date(
                            cls.get_date_of_first_delivery(
                                location_change_valid_from=valid_from,
                                member=member,
                                pickup_location_id=pickup_location_id,
                                cache=cache,
                            )
                        ),
                        "address": UserUtils.build_display_address(
                            street=pickup_location.street,
                            street_2=pickup_location.street_2,
                            postcode=pickup_location.postcode,
                            city=pickup_location.city,
                        ),
                        "access_code": pickup_location.access_code,
                        "messenger_group_link": pickup_location.messenger_group_link,
                        "contact_name": pickup_location.contact_name,
                        "photo_link": pickup_location.photo_link,
                        "infos": pickup_location.info,
                        "opening_times": PickupLocationOpeningTimesFormatter.get_formatted_opening_times(
                            pickup_location_id=pickup_location_id, cache=cache
                        ),
                    },
                ),
            )

    @classmethod
    def get_date_of_first_delivery(
        cls,
        location_change_valid_from: datetime.date,
        member: Member,
        pickup_location_id: str,
        cache: dict,
    ):
        deliveries = GetDeliveriesService.get_deliveries(
            member=member,
            date_from=location_change_valid_from,
            date_to=location_change_valid_from + datetime.timedelta(days=365),
            cache=cache,
        )

        for delivery in deliveries:
            if delivery["is_delivery_cancelled_this_week"]:
                continue
            return delivery["delivery_date"]

        return DeliveryDateCalculator.get_next_delivery_date_any_product(
            reference_date=location_change_valid_from,
            pickup_location_id=pickup_location_id,
            cache=cache,
        )
