from django import template
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from tapir.core.models import SidebarLinkGroup

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

    if request.user.has_perm("coop.admin"):
        add_admin_links(groups)

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


def add_admin_links(groups):
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
    admin_group.add_link(
        display_name=_("Konfiguration"),
        material_icon="settings",
        url=reverse_lazy("configuration:parameters"),
    )
    admin_group.add_link(
        display_name=_("Anbauperiode & Produkte"),
        material_icon="agriculture",
        url=reverse_lazy("wirgarten:product"),
    )
    admin_group.add_link(
        display_name=_("Abholorte"),
        material_icon="add_location_alt",
        url=reverse_lazy("wirgarten:pickup_locations"),
    )
    admin_group.add_link(
        display_name=_("Lastschrift"),
        material_icon="account_balance",
        url=reverse_lazy("wirgarten:payment_transactions"),
    )

    members_group = SidebarLinkGroup(name=_("Mitglieder"))
    members_group.add_link(
        display_name=(_("Mitglieder")),
        material_icon="groups",
        url=reverse_lazy("wirgarten:member_list"),
    )

    groups.append(members_group)
    groups.append(admin_group)
    groups.append(debug_group)
