from django import template

from tapir.wirgarten.views import FORM_TITLES

register = template.Library()


@register.filter(name="get_value")
def get_value(dictionary, key):
    if type(dictionary) is dict:
        return dictionary.get(key)
    else:
        return None


@register.filter(name="get_step_title")
def get_step_title(step):
    return FORM_TITLES.get(step, step)


@register.inclusion_tag(
    "wirgarten/registration/steps/components/summary_card_disabled.html"
)
def summary_card_disabled(title):
    return {"title": title}
