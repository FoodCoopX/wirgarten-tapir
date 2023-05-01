from django import template
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from tapir.core.models import SidebarLinkGroup
from tapir.wirgarten.constants import Permission  # FIXME: circular dependency :(
from tapir.wirgarten.models import Subscription, CoopShareTransaction, WaitingListEntry
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_future_subscriptions,
    get_current_growing_period,
)

register = template.Library()


@register.inclusion_tag("core/sidebar_links.html", takes_context=True)
def sidebar_links(context):
    groups = get_sidebar_link_groups(context["request"])

    for group in groups:
        for link in group.links:
            link["is_active"] = link["url"] == context["request"].path

    context["sidebar_link_groups"] = groups

    return context


def get_sidebar_link_groups(request):
    groups = []

    if request.user.has_perm(Permission.Coop.VIEW):
        add_admin_links(groups, request)

    # misc_group = SidebarLinkGroup(name=_("Miscellaneous"))
    # groups.append(misc_group)
    # misc_group.add_link(
    #    display_name=_("Wiki"),
    #    material_icon="feed",
    #    url="https://wiki.supercoop.de",
    # )
    # misc_group.add_link(
    #    display_name=_("Member manual"),
    #    material_icon="menu_book",
    #    url="https://wiki.supercoop.de/wiki/Member_Manual",
    # )
    # misc_group.add_link(
    #    display_name=_("Shop opening hours"),
    #    material_icon="access_time",
    #    url="https://wiki.supercoop.de/wiki/%C3%96ffnungszeiten",
    # )
    # misc_group.add_link(
    #    display_name=_("Contact the member office"),
    #    material_icon="email",
    #    url="mailto:mitglied@supercoop.de",
    # )
    #   misc_group.add_link(
    #       display_name=_("About tapir"),
    #       material_icon="help",
    #       url=reverse_lazy("coop:about"),
    #   )

    return groups


def add_admin_links(groups, request):
    debug_group = SidebarLinkGroup(name=_("Debug"))
    debug_group.add_link(
        display_name=_("Exportierte Dateien"),
        material_icon="attach_file",
        url=reverse_lazy("wirgarten:exported_files_list"),
    )

    admin_group = SidebarLinkGroup(name=_("Administration"))
    admin_group.add_link(
        display_name=_("Dashboard"),
        material_icon="dashboard",
        url=reverse_lazy("wirgarten:admin_dashboard"),
    )
    if request.user.has_perm(Permission.Coop.MANAGE):
        admin_group.add_link(
            display_name=_("Konfiguration"),
            material_icon="settings",
            url=reverse_lazy("configuration:parameters"),
        )
    if request.user.has_perm(Permission.Products.VIEW):
        admin_group.add_link(
            display_name=_("Anbauperiode & Produkte"),
            material_icon="agriculture",
            url=reverse_lazy("wirgarten:product"),
        )
    if request.user.has_perm(Permission.Coop.VIEW):
        admin_group.add_link(
            display_name=_("Abholorte"),
            material_icon="add_location_alt",
            url=reverse_lazy("wirgarten:pickup_locations"),
        )
    if request.user.has_perm(Permission.Payments.VIEW):
        admin_group.add_link(
            display_name=_("Lastschrift"),
            material_icon="account_balance",
            url=reverse_lazy("wirgarten:payment_transactions"),
        )

    if request.user.has_perm(Permission.Accounts.VIEW):
        members_group = SidebarLinkGroup(name=_("Mitglieder"))
        members_group.add_link(
            display_name=(_("Mitglieder")),
            material_icon="groups",
            url=reverse_lazy("wirgarten:member_list"),
        )

        members_group.add_link(
            display_name=_("Verträge"),
            material_icon="history_edu",
            url=reverse_lazy("wirgarten:subscription_list"),
        )

        coop_shares = CoopShareTransaction.objects.filter(
            admin_confirmed__isnull=True,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        ).count()
        product_shares = Subscription.objects.filter(
            admin_confirmed__isnull=True
        ).count()

        members_group.add_link(
            display_name=_("Neue Zeichnungen"),
            material_icon="approval_delegation",
            url=reverse_lazy("wirgarten:new_contracts"),
            notification_count=coop_shares + product_shares,
        )

        waitlist_entries = WaitingListEntry.objects.count()
        members_group.add_link(
            display_name=_("Warteliste"),
            material_icon="schedule",
            url=reverse_lazy("wirgarten:waitinglist"),
            notification_count=waitlist_entries,
        )

        groups.append(members_group)
    groups.append(admin_group)

    groups.append(debug_group)
