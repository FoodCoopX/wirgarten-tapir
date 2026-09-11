from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """{{ mydict|get_item:key }} → mydict[key]"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, "")
    return None
