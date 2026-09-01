from django import template

register = template.Library()


def _route_basket_totals(entry: dict) -> dict:
    return entry.get("route_basket_totals") or {}


def _header_value(totals: dict | None, header) -> int:
    value = (totals or {}).get(header)
    return value or 0


@register.simple_tag(takes_context=True)
def sum_pickup_location_basket_totals(context, header, *pickup_location_names):
    names = set(pickup_location_names)
    total = 0
    for entry in context.get("entries") or []:
        for pickup_location in (
            _route_basket_totals(entry).get("pickup_location_data") or []
        ):
            if pickup_location.get("name") in names:
                total += _header_value(pickup_location.get("totals"), header)
    return total


@register.simple_tag(takes_context=True)
def sum_location_route_basket_totals(context, header, *route_names):
    names = set(route_names)
    total = 0
    for entry in context.get("entries") or []:
        if entry.get("route_name") in names:
            total += _header_value(_route_basket_totals(entry).get("totals"), header)
    return total
