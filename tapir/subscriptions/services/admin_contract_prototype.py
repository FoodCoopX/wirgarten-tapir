"""Read-only data and capacity checks for the admin UI prototype (issue #1037)."""

import datetime
import re

from django.db.models import Q
from tapir.coop.services.member_number_service import MemberNumberService

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.pickup_location_active_filter import (
    PickupLocationActiveFilter,
)
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    PickupLocation,
    Product,
    Subscription,
)
from tapir.wirgarten.utils import get_today


class AdminContractPrototype:
    @staticmethod
    def search(query: str, cache: dict):
        members = Member.objects.all()
        for token in query.split():
            name_match = (
                Q(first_name__icontains=token)
                | Q(last_name__icontains=token)
                | Q(pk=token)
            )
            number = re.fullmatch(r"[^\d\s]*(\d+)", token)
            if number:
                name_match |= Q(member_no=int(number.group(1)))
            members = members.filter(name_match)
        return [
            {
                "id": m.id,
                "name": f"{m.first_name} {m.last_name}",
                "number": MemberNumberService.format_member_number(
                    m.member_no, cache=cache
                ),
            }
            for m in members.order_by("last_name", "first_name")[:15]
        ]

    @staticmethod
    def configuration(cache: dict):
        today = get_today(cache=cache)
        periods = list(
            GrowingPeriod.objects.filter(end_date__gte=today).order_by("start_date")
        )
        next_start = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=today, apply_buffer_time=True, cache=cache
        )
        earliest_monday = today + datetime.timedelta(days=(-today.weekday()) % 7)
        min_week = earliest_monday.isocalendar()
        current = next(
            (p for p in periods if p.start_date <= today <= p.end_date), None
        )
        max_week = current.end_date.isocalendar() if current else None
        return {
            "today": today,
            "minWeek": f"{min_week.year}-W{min_week.week:02}",
            "maxWeek": f"{max_week.year}-W{max_week.week:02}" if max_week else "",
            "nextStart": next_start,
            "periods": [
                {"id": p.id, "start": p.start_date, "end": p.end_date} for p in periods
            ],
            "products": list(
                Product.objects.filter(deleted=False).values(
                    "id", "name", "type_id", "type__name"
                )
            ),
            "rhythms": [
                choice
                for choice in MemberPaymentRhythm.Rhythm.choices
                if MemberPaymentRhythmService.is_payment_rhythm_allowed(
                    choice[0], cache=cache
                )
            ],
        }

    @staticmethod
    def member(member_id: str, cache: dict):
        member = Member.objects.get(pk=member_id)
        today = get_today(cache=cache)
        location = member.get_pickup_location(reference_date=today)
        rhythm = (
            member.memberpaymentrhythm_set.filter(valid_from__lte=today)
            .order_by("-valid_from")
            .first()
        )
        return {
            "id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "number": MemberNumberService.format_member_number(
                member.member_no, cache=cache
            ),
            "bankPresent": bool(member.iban and member.account_owner),
            "rhythm": rhythm.get_rhythm_display() if rhythm else None,
            "location": (
                {"id": location.id, "name": location.name} if location else None
            ),
            "contracts": [
                {
                    "id": s.id,
                    "selectionId": f"{s.id}:{unit}",
                    "unit": unit,
                    "originalQuantity": s.quantity,
                    "priceCategory": (
                        "exempt"
                        if s.price_override == 0
                        else "custom" if s.price_override is not None else "standard"
                    ),
                    "productId": s.product_id,
                    "typeId": s.product.type_id,
                    "type": s.product.type.name,
                    "product": s.product.name,
                    "quantity": 1,
                    "start": s.start_date,
                    "end": s.end_date,
                    "cancelled": bool(s.cancellation_ts),
                    "ended": s.end_date < today,
                }
                for s in member.subscription_set.select_related(
                    "product__type"
                ).order_by("-start_date")
                for unit in range(1, s.quantity + 1)
            ],
        }

    @staticmethod
    def preview(params, cache: dict):
        member = Member.objects.get(pk=params["member"])
        product = Product.objects.select_related("type").get(
            pk=params["product"], deleted=False
        )
        quantity = int(params["quantity"])
        start = datetime.date.fromisoformat(params["start"])
        today = get_today(cache=cache)
        if start < today:
            raise ValueError(
                "Der Vertragsbeginn darf nicht in der Vergangenheit liegen."
            )
        period = GrowingPeriod.objects.get(start_date__lte=start, end_date__gte=start)
        if quantity < 1 or quantity > 32767:
            raise ValueError("Die Menge ist ungültig.")
        contract_id = params.get("contract")
        contract = None
        if contract_id:
            contract = Subscription.objects.get(pk=contract_id, member=member)
            unit = int(params.get("unit", "1"))
            if (
                contract.cancellation_ts
                or quantity != 1
                or not 1 <= unit <= contract.quantity
                or contract.end_date < today
                or contract.product.type_id != product.type_id
            ):
                raise ValueError("Dieser Vertrag kann nicht geändert werden.")
        order = {product: quantity}
        if contract and contract.quantity > 1:
            order[contract.product] = (
                order.get(contract.product, 0) + contract.quantity - 1
            )
        # The existing checkers subtract the member's current subscriptions. Include
        # unchanged quantities so an addition cannot accidentally reclaim their capacity.
        for existing in member.subscription_set.select_related("product").filter(
            start_date__lte=start, end_date__gte=start
        ):
            if (
                existing.id != contract_id
                and existing.product.type_id == product.type_id
            ):
                order[existing.product] = (
                    order.get(existing.product, 0) + existing.quantity
                )
        global_ok = not GlobalCapacityChecker.get_product_type_ids_without_enough_capacity_for_order(
            order_with_all_product_types=order,
            member_id=member.id,
            subscription_start_date=start,
            cache=cache,
        )
        product_ok = all(
            ProductCapacityChecker.does_product_have_enough_free_capacity_to_add_order(
                product=p,
                ordered_quantity=q,
                member_id=member.id,
                subscription_start_date=start,
                cache=cache,
            )
            for p, q in order.items()
        )
        locations = [
            {"id": location.id, "name": location.name}
            for location in PickupLocationActiveFilter.get_active_at_date(
                PickupLocation.objects.order_by("name"), start
            )
            if PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                pickup_location=location,
                order=order,
                already_registered_member=member,
                subscription_start=start,
                cache=cache,
            )
        ]
        return {
            "globalOkay": global_ok,
            "productOkay": product_ok,
            "locations": locations,
            "end": period.end_date,
        }
