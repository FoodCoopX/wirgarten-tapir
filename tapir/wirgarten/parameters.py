import datetime
from decimal import Decimal

from tapir.configuration.models import (
    TapirParameterDatatype,
    TapirParameterDefinitionImporter,
    TapirParameter,
)
from tapir.configuration.parameter import ParameterMeta, parameter_definition
from tapir.wirgarten.parameter_definitions.parameter_definitions_bestellwizard import (
    ParameterDefinitionsBestellwizard,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_business import (
    ParameterDefinitionsBusiness,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_delivery import (
    ParameterDefinitionsDelivery,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_emails import (
    ParameterDefinitionsEmails,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_jokers import (
    ParameterDefinitionsJokers,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_member_dashboard import (
    ParameterDefinitionsMemberDashboard,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_organization import (
    ParameterDefinitionsOrganization,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_payments import (
    ParameterDefinitionsPayments,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_picking import (
    ParameterDefinitionsPicking,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_site import (
    ParameterDefinitionsSite,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_solidarity import (
    ParameterDefinitionsSolidarity,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_subscriptions import (
    ParameterDefinitionsSubscriptions,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_supplier_list import (
    ParameterDefinitionsSupplierList,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_test import (
    ParameterDefinitionsTest,
)
from tapir.wirgarten.parameter_definitions.parameter_definitions_trial_period import (
    ParameterDefinitionsTrialPeriod,
)


class ParameterDefinitions(TapirParameterDefinitionImporter):
    def __init__(self):
        self.parameters_to_create = []
        self.no_db_request = False

    def import_definitions(self, bulk_create=False):
        self.no_db_request = bulk_create
        self.define_all_parameters()
        if bulk_create:
            TapirParameter.objects.bulk_create(self.parameters_to_create)

    def define_all_parameters(self):
        ParameterDefinitionsBestellwizard.define_all_member_bestellwizard(importer=self)
        ParameterDefinitionsBusiness.define_all_member_business(importer=self)
        ParameterDefinitionsDelivery.define_all_parameters_delivery(importer=self)
        ParameterDefinitionsEmails.define_all_parameters_emails(importer=self)
        ParameterDefinitionsJokers.define_all_parameters_jokers(importer=self)
        ParameterDefinitionsMemberDashboard.define_all_parameters_member_dashboard(
            importer=self
        )
        ParameterDefinitionsOrganization.define_all_parameters_organization(
            importer=self
        )
        ParameterDefinitionsPayments.define_all_parameters_payments(importer=self)
        ParameterDefinitionsPicking.define_all_parameters_picking(importer=self)
        ParameterDefinitionsSite.define_all_parameters_site(importer=self)
        ParameterDefinitionsSolidarity.define_all_parameters_solidarity(importer=self)
        ParameterDefinitionsSubscriptions.define_all_parameters_subscriptions(
            importer=self
        )
        ParameterDefinitionsSupplierList.define_all_parameters_supplier_list(
            importer=self
        )
        ParameterDefinitionsTest.define_all_parameters_test(importer=self)
        ParameterDefinitionsTrialPeriod.define_all_parameters_trial_period(
            importer=self
        )

    def parameter_definition(
        self,
        key: str,
        label: str,
        description: str,
        category: str,
        datatype: TapirParameterDatatype,
        initial_value: str | int | float | bool | datetime.date | Decimal,
        order_priority: int = -1,
        enabled: bool = True,
        debug: bool = False,
        meta: ParameterMeta = ParameterMeta(
            options=None, validators=[], vars_hint=None, textarea=False
        ),
    ):
        parameter_to_create = parameter_definition(
            key=key,
            label=label,
            description=description,
            category=category,
            datatype=datatype,
            initial_value=initial_value,
            order_priority=order_priority,
            enabled=enabled,
            debug=debug,
            meta=meta,
            no_db_request=self.no_db_request,
        )

        if self.no_db_request:
            self.parameters_to_create.append(parameter_to_create)
