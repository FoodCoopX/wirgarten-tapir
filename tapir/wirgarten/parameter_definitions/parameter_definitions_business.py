import typing
from decimal import Decimal

from django.core.validators import URLValidator, MinValueValidator

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.coop.services.coop_share_instalment_config_validator import (
    CoopShareInstalmentConfigValidator,
)
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import (
    legal_status_is_cooperative,
    legal_status_is_association,
)

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsBusiness:
    @classmethod
    def define_all_member_business(cls, importer: ParameterDefinitions):
        order_priority = 1000
        importer.parameter_definition(
            key=ParameterKeys.COOP_MIN_SHARES,
            label="Mindestanzahl Genossenschaftsanteile",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Die Mindestanzahl der Genossenschaftsanteile die ein neues Mitglied zeichnen muss.",
            category=ParameterCategory.BUSINESS,
            order_priority=order_priority,
            meta=ParameterMeta(
                validators=[MinValueValidator(limit_value=0)],
                show_only_when=legal_status_is_cooperative,
            ),
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.COOP_SHARE_PRICE,
            label="Preis für einer Anteil",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=50,
            description="",
            category=ParameterCategory.BUSINESS,
            order_priority=order_priority,
            meta=ParameterMeta(
                validators=[MinValueValidator(limit_value=0)],
                show_only_when=legal_status_is_cooperative,
            ),
            enabled=is_debug_instance(),
        )
        order_priority -= 1

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
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.COOP_INFO_LINK,
            label="Link zu weiteren Infos über der Betrieb",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/genossenschaft/",
            description="Der Link zu weiteren Infos über der Betrieb.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(validators=[URLValidator()]),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.COOP_THRESHOLD_WARNING_ON_MANY_COOP_SHARES_BOUGHT,
            label="Schwelle Anzahl an Geno-Anteile bei Zeichnungen",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=10,
            description="Wenn mehr als der angegebene Anzahl an Geno-Anteile gezeichnet werden, wird ein Mail an der Admin versendet.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(show_only_when=legal_status_is_cooperative),
            order_priority=order_priority,
        )
        order_priority -= 1

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
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.COOP_SHARES_INSTALMENTS_ENABLED,
            label="Ratenzahlung des Pflichtanteils",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Neue Mitglieder können im Bestellwizard den Pflichtanteil in monatlichen Raten zahlen. Der Pflichtanteil ist die Mindestanzahl an Genossenschaftsanteilen, die sich aus der Konfiguration und den bestellten Produkten ergibt. Die Ratenzahlung ist nur möglich, wenn das Mitglied genau diese Mindestanzahl zeichnet: werden mehr Anteile gezeichnet, muss der gesamte Betrag auf einmal gezahlt werden.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(show_only_when=legal_status_is_cooperative),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.COOP_SHARES_INSTALMENT_AMOUNT,
            label="Höhe einer Rate",
            datatype=TapirParameterDatatype.DECIMAL,
            # 1 because the share price is an integer, so it is always divisible by 1
            initial_value=Decimal(1),
            description="Betrag in € einer monatlichen Rate. Der Preis eines Anteils muss durch diesen Betrag teilbar sein. Die Anzahl der Raten ergibt sich aus dem Betrag des Pflichtanteils.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(
                validators=[
                    MinValueValidator(limit_value=Decimal("0.01")),
                    CoopShareInstalmentConfigValidator.validate_instalment_amount,
                ],
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.COOP_SHARES_INSTALMENTS_ENABLED, cache=cache
                ),
            ),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATIONS_ALLOW_SUPPORTING_MEMBERSHIP,
            label="Fördermitgliedschaften erlauben",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn ausgeschaltet, ist es nicht möglich eine Vereinsmitgliedschaft abzuschließen ohne dabei ein Produktvertrag abzuschließen. Das wirkt nur in der Intro-Seite des BestellWizards.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(show_only_when=legal_status_is_association),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATIONS_ENABLE_ASSOCIATION_MEMBERSHIPS,
            label="Neue Vereinsmitgliedschaften aktivieren",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(show_only_when=legal_status_is_association),
            order_priority=order_priority,
        )
        order_priority -= 1
