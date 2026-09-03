from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def sum_pickup_location_basket_totals(context, header, *pickup_location_names):
    names = set(pickup_location_names)
    total = 0
    for entry in context.get("entries", []):
        for pickup_location in entry.get("route_basket_totals", {}).get(
            "pickup_location_data", []
        ):
            if pickup_location.get("name") in names:
                total += pickup_location.get("totals", {}).get(header, 0)
    return total


@register.simple_tag(takes_context=True)
def sum_location_route_basket_totals(context, header, *route_names):
    names = set(route_names)
    total = 0
    for entry in context.get("entries", []):
        if entry.get("route_name") in names:
            total += entry.get("route_basket_totals", {}).get("totals", {}).get(
                header, 0
            )
    return total
