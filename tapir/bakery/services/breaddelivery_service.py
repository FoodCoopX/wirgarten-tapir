from datetime import date, datetime, timedelta

from django.db import models

from tapir.wirgarten.models import Member, Subscription


def get_weeks_in_range(start_date, end_date):
    """
    Generator that yields (year, week_number) tuples for all weeks between start_date and end_date.
    """
    current_date = start_date
    while current_date <= end_date:
        iso_calendar = current_date.isocalendar()
        yield (iso_calendar[0], iso_calendar[1])
        current_date += timedelta(weeks=1)


_sync_in_progress = set()


def _get_bread_delivery_model():
    from tapir.bakery.models import BreadDelivery

    return BreadDelivery


def ensure_bread_deliveries_for_member(member: Member):

    if member.pk in _sync_in_progress:
        return
    _sync_in_progress.add(member.pk)

    try:
        _sync_deliveries(member)
    finally:
        _sync_in_progress.discard(member.pk)


def _sync_deliveries(member: Member):
    now = datetime.now().date()
    current_iso = now.isocalendar()
    current_year, current_week = current_iso[0], current_iso[1]

    pickup_location = _resolve_pickup_location(member, now)

    _sync_relevant_subscriptions(member, now, pickup_location)
    _update_future_pickup_locations(member, current_year, current_week, pickup_location)
    _sync_joker_status(member)
    _cleanup_expired_subscriptions(member, now, current_year, current_week)


def _resolve_pickup_location(member: Member, reference_date):
    try:
        return member.get_pickup_location(reference_date)
    except Exception:
        return None


def _sync_relevant_subscriptions(member, now, pickup_location):
    relevant_subscriptions = Subscription.objects.filter(
        member=member,
        end_date__gte=now,
    ).select_related("product__type")

    for subscription in relevant_subscriptions:
        if subscription.product.type.delivery_cycle != "weekly":
            continue
        if not subscription.start_date or not subscription.end_date:
            continue

        _sync_subscription_deliveries(subscription, pickup_location)


def _sync_subscription_deliveries(subscription, pickup_location):
    target_quantity = subscription.quantity
    weeks_in_period = list(
        get_weeks_in_range(subscription.start_date, subscription.end_date)
    )
    valid_year_weeks = set(weeks_in_period)

    member = subscription.member
    for year, week in weeks_in_period:
        # Get correct pickup location for this specific week
        delivery_date = date.fromisocalendar(year, week, 1)  # Monday of that week
        week_pickup_location = member.get_pickup_location(delivery_date)
        _ensure_correct_slot_count(
            subscription, year, week, target_quantity, week_pickup_location
        )

    _delete_deliveries_outside_period(subscription, valid_year_weeks)


def _ensure_correct_slot_count(
    subscription, year, week, target_quantity, pickup_location
):
    BreadDelivery = _get_bread_delivery_model()
    existing_deliveries = BreadDelivery.objects.filter(
        subscription=subscription, year=year, delivery_week=week
    ).order_by("slot_number")

    existing_count = existing_deliveries.count()

    if existing_count < target_quantity:
        for slot_number in range(existing_count + 1, target_quantity + 1):
            BreadDelivery.objects.create(
                subscription=subscription,
                year=year,
                delivery_week=week,
                slot_number=slot_number,
                pickup_location=pickup_location,
                bread=None,
            )
    elif existing_count > target_quantity:
        deliveries_to_remove = existing_deliveries[target_quantity:]
        for delivery in deliveries_to_remove:
            delivery.delete()


def _delete_deliveries_outside_period(subscription, valid_year_weeks):
    BreadDelivery = _get_bread_delivery_model()
    all_deliveries = BreadDelivery.objects.filter(subscription=subscription)
    ids_to_keep = [
        d.id for d in all_deliveries if (d.year, d.delivery_week) in valid_year_weeks
    ]
    to_delete = all_deliveries.exclude(id__in=ids_to_keep)
    to_delete.delete()


def _update_future_pickup_locations(
    member, current_year, current_week, pickup_location
):
    """
    Update pickup locations for future deliveries, considering valid_from dates.
    Each delivery gets the pickup location that's valid for its delivery week.
    If pickup_location changes, bread assignment is cleared (may not be available at new location).
    """
    BreadDelivery = _get_bread_delivery_model()
    future_deliveries = BreadDelivery.objects.filter(
        subscription__member=member,
    ).filter(
        models.Q(year__gt=current_year)
        | models.Q(year=current_year, delivery_week__gte=current_week)
    )

    for delivery in future_deliveries:
        # Calculate the Monday of the delivery week as reference date
        delivery_date = date.fromisocalendar(delivery.year, delivery.delivery_week, 1)
        correct_pickup_location = member.get_pickup_location(delivery_date)

        if (
            correct_pickup_location
            and delivery.pickup_location_id != correct_pickup_location.id
        ):
            delivery.pickup_location = correct_pickup_location
            # Clear bread assignment since it may not be available at the new location
            delivery.bread = None
            delivery.save(update_fields=["pickup_location", "bread"])


def _sync_joker_status(member):
    from tapir.deliveries.models import Joker

    BreadDelivery = _get_bread_delivery_model()

    joker_weeks = set()
    for joker in Joker.objects.filter(member=member):
        iso_year, iso_week, _ = joker.date.isocalendar()
        joker_weeks.add((iso_year, iso_week))

    deliveries = BreadDelivery.objects.filter(subscription__member=member)

    if joker_weeks:
        joker_q = models.Q()
        for year, week in joker_weeks:
            joker_q |= models.Q(year=year, delivery_week=week)
        deliveries.filter(joker_q).update(joker_taken=True)
        deliveries.exclude(joker_q).update(joker_taken=False)
    else:
        deliveries.update(joker_taken=False)


def _cleanup_expired_subscriptions(member, now, current_year, current_week):
    BreadDelivery = _get_bread_delivery_model()
    expired_subscriptions = Subscription.objects.filter(
        member=member,
        end_date__lt=now,
    )
    for subscription in expired_subscriptions:
        to_delete = BreadDelivery.objects.filter(
            subscription=subscription,
        ).filter(
            models.Q(year__gt=current_year)
            | models.Q(year=current_year, delivery_week__gt=current_week)
        )
        to_delete.delete()
