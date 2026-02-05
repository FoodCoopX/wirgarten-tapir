import typing

from django.conf import settings
from django.core.validators import URLValidator, MinValueValidator

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.models import ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_cooperative
from tapir.wirgarten.validators import validate_base_product_type_exists

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsBusiness:
    @classmethod
    def define_all_member_business(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.COOP_MIN_SHARES,
            label="Mindestanzahl Genossenschaftsanteile",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Die Mindestanzahl der Genossenschaftsanteile die ein neues Mitglied zeichnen muss.",
            category=ParameterCategory.BUSINESS,
            order_priority=1000,
            meta=ParameterMeta(
                validators=[MinValueValidator(limit_value=0)],
                show_only_when=legal_status_is_cooperative,
            ),
        )

        importer.parameter_definition(
            key=ParameterKeys.COOP_SHARE_PRICE,
            label="Preis für einer Anteil",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=50,
            description="",
            category=ParameterCategory.BUSINESS,
            order_priority=999,
            meta=ParameterMeta(
                validators=[MinValueValidator(limit_value=0)],
                show_only_when=legal_status_is_cooperative,
            ),
            enabled=is_debug_instance(),
        )

        importer.parameter_definition(
            key=ParameterKeys.COOP_STATUTE_LINK,
            label="Link zur Satzung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/satzung",
            description="Der Link zur Satzung des Betriebs.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(
                validators=[URLValidator()],
                show_only_when=legal_status_is_cooperative,
            ),
        )

        importer.parameter_definition(
            key=ParameterKeys.COOP_INFO_LINK,
            label="Link zu weiteren Infos über der Betrieb",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/genossenschaft/",
            description="Der Link zu weiteren Infos über der Betrieb.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

        importer.parameter_definition(
            key=ParameterKeys.COOP_THRESHOLD_WARNING_ON_MANY_COOP_SHARES_BOUGHT,
            label="Schwelle Anzahl an Geno-Anteile bei Zeichnungen",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=10,
            description="Wenn mehr als der angegebene Anzahl an Geno-Anteile gezeichnet werden, wird ein Mail an der Admin versendet.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(show_only_when=legal_status_is_cooperative),
        )

        importer.parameter_definition(
            key=ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES,
            label="Genossenschaftsanteile separat von Ernteanteilen zeichenbar",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Genossenschaftsanteile sind vom Mitglied separat von Ernteanteilen zeichenbar.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(
                options=[
                    (True, "separat zeichenbar"),
                    (False, "nicht separat zeichenbar"),
                ],
                show_only_when=legal_status_is_cooperative,
            ),
            order_priority=800,
        )

        def get_default_product_type():
            if not hasattr(settings, "BASE_PRODUCT_NAME"):
                raise ValueError(
                    "BASE_PRODUCT_NAME is not set in tapir/wirgarten/settings/site.py"
                )

            default_product_type = ProductType.objects.filter(
                name=settings.BASE_PRODUCT_NAME
            )
            return (
                default_product_type.first().id
                if default_product_type.exists()
                else None
            )

        importer.parameter_definition(
            key=ParameterKeys.COOP_BASE_PRODUCT_TYPE,
            label="Basis Produkttyp",
            datatype=TapirParameterDatatype.STRING,
            initial_value=get_default_product_type(),
            description="Der Basis Produkttyp. Wird als erste im BestellWizard angezeigt.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(
                options_callable=lambda cache: [
                    (product_type.id, product_type.name)
                    for product_type in ProductType.objects.all()
                ],
                validators=[validate_base_product_type_exists],
            ),
            enabled=True,
        )
