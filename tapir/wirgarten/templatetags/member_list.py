from django import template

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today

register = template.Library()


@register.inclusion_tag("wirgarten/template_tags/pickup_location_warning.html")
def pickup_location_warning(member: Member, cache: dict):
    context = {"show_warning": False, "member_id": member.id}
    pickup_location_id = MemberPickupLocationGetter.get_member_pickup_location_id(
        member=member, reference_date=get_today(cache=cache)
    )
    if pickup_location_id is None:
        return context

    subscriptions = TapirCache.get_active_and_future_subscriptions_by_member_id(
        cache=cache, reference_date=get_today(cache=cache)
    ).get(member.id, [])
    if len(subscriptions) > 0:
        return context

    context["show_warning"] = True
    return context


@register.simple_tag()
def member_email_verified(member: Member, cache: dict):
    return member.email_verified(cache)


@register.simple_tag()
def formatted_member_number(member: Member, cache=None):
    if cache is None:
        cache = {}
    return (
        MemberNumberService.format_member_number(member.member_no, cache=cache) or "-"
    )
