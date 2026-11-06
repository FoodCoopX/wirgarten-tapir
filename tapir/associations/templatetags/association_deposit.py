from django import template

from tapir.associations.services.association_deposit_overview_provider import (
    AssociationDepositOverviewProvider,
)

register = template.Library()


@register.inclusion_tag("associations/deposit_overview_cell.html")
def deposit_overview_cell(member, cache: dict):
    return {"deposit": AssociationDepositOverviewProvider.get_row(member, cache)}
