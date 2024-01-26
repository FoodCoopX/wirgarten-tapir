from django import template

from django.conf import settings


register = template.Library()


def get_step_settings(step):
    return settings.REGISTRATION_STEPS.get(step, {})


@register.filter(name="get_step_title")
def get_step_title(step):
    return get_step_settings(step).get("title", None)


@register.filter(name="get_step_description")
def get_step_description(step):
    return get_step_settings(step).get("description", None)


@register.inclusion_tag("wirgarten/registration/components/summary_card_disabled.html")
def summary_card_disabled(title):
    return {"title": title}
