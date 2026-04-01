import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsSupplierList:
    @classmethod
    def define_all_parameters_supplier_list(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.SUPPLIER_LIST_PRODUCT_TYPES,
            label="Produkte für Lieferantenlisten",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Hühneranteile",
            description="Komma-separierte Liste der Zusatzabos für die eine Lieferantenliste erzeugt werden soll.",
            category=ParameterCategory.SUPPLIER_LIST,
        )

        importer.parameter_definition(
            key=ParameterKeys.SUPPLIER_LIST_SEND_ADMIN_EMAIL,
            label="Automatische Email an Admin",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiv, dann wird automatisch wöchentlich eine Email mit den Lieferantenlisten an den Admin versandt.",
            category=ParameterCategory.SUPPLIER_LIST,
        )
