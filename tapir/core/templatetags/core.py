from django import template
from django.core.handlers.wsgi import WSGIRequest
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from tapir.core.models import SidebarLinkGroup
from tapir.wirgarten.constants import Permission  # FIXME: circular dependency :(
from tapir.wirgarten.models import Subscription, CoopShareTransaction, WaitingListEntry

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

    return groups


def add_admin_links(groups, request):
    debug_group = SidebarLinkGroup(name=_("Debug"))
    debug_group.add_link(
        display_name=_("Exportierte Dateien"),
        material_icon="attach_file",
        url=reverse_lazy("wirgarten:exported_files_list"),
    )
    debug_group.add_link(
        display_name=_("Geplante Tasks"),
        material_icon="pending_actions",
        url=reverse_lazy("wirgarten:scheduled_tasks"),
    )
    debug_group.add_link(
        display_name=_("Jobs"),
        material_icon="event_repeat",
        url=reverse_lazy("wirgarten:jobs"),
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

    if request.user.has_perm(Permission.Email.MANAGE):
        admin_group.add_link(
            display_name=_("E-Mail"),
            material_icon="email",
            url=reverse_lazy("tapir_mail"),
        )

    if request.user.has_perm(Permission.Payments.VIEW):
        admin_group.add_link(
            display_name=_("Lastschrift"),
            material_icon="account_balance",
            url=reverse_lazy("wirgarten:payment_transactions"),
        )

    if request.user.has_perm(Permission.Coop.MANAGE):
        admin_group.add_link(
            display_name=_("CSV-Exports"),
            material_icon="attach_file",
            url=reverse_lazy("generic_exports:csv_export_editor"),
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


@register.inclusion_tag(
    "core/tags/javascript_environment_variables.html", takes_context=True
)
def javascript_environment_variables(context):
    request: WSGIRequest = context["request"]
    api_root = f"{'https' if request.is_secure() else 'http'}://{request.get_host()}"
    if request.get_host() == "localhost":
        api_root = f"{api_root}:8000"
    return {
        "env_vars": {"REACT_APP_API_ROOT": api_root},
    }
