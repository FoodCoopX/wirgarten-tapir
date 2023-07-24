from django import template
from django.urls import reverse

from tapir.log.models import LogEntry

register = template.Library()


@register.inclusion_tag("log/log_entry_list_tag.html", takes_context=True)
def user_log_entry_list(context, selected_user):
    raw_entries = LogEntry.objects.filter(user=selected_user).order_by("-created_date")
    log_entries = [entry.as_leaf_class() for entry in raw_entries]
    context["log_entries"] = log_entries

    context["create_text_log_entry_action_url"] = "%s?next=%s" % (
        reverse("log:create_user_text_log_entry", args=[selected_user.pk]),
        reverse("wirgarten:member_detail", args=[selected_user.pk]),
    )

    return context
