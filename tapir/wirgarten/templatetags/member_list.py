from django import template

from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_today

register = template.Library()


@register.inclusion_tag("wirgarten/template_tags/pickup_location_warning.html")
def pickup_location_warning(member: Member, cache: dict):
    context = {"show_warning": False, "member_id": member.id}
    pickup_location_id = MemberPickupLocationService.get_member_pickup_location_id(
        member=member, reference_date=get_today(cache=cache)
    )
    if pickup_location_id is None:
        return context

    if (
        get_active_and_future_subscriptions(
            reference_date=get_today(cache=cache), cache=cache
        )
        .filter(member=member)
        .exists()
    ):
        return context

    context["show_warning"] = True
    return context


@register.simple_tag()
def member_email_verified(member: Member, cache: dict):
    return member.email_verified(cache)
