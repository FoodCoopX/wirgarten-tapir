import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.deliveries.config import (
    DELIVERY_DONATION_MODE_DISABLED,
    DELIVERY_DONATION_MODE_OPTIONS,
    DELIVERY_DONATION_DONT_FORWARD_TO_PICKUP_LOCATION,
    NO_SOLIDARITY_CONTRIBUTION_IN_JOKER_CREDITS,
)
from tapir.wirgarten.constants import (
    ParameterCategory,
    HTML_ALLOWED_TEXT,
    CUSTOM_CYCLE,
)
from tapir.wirgarten.models import PickupLocation, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsJokers:
    @classmethod
    def define_all_parameters_jokers(cls, importer: ParameterDefinitions):
        order_priority = 100
        importer.parameter_definition(
            key=ParameterKeys.JOKERS_ENABLED,
            label="Joker-Feature einschalten",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Temporäre Liefer-Pausen pro Mitglied erlauben",
            category=ParameterCategory.JOKERS,
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.JOKERS_CREATE_MEMBER_CREDITS,
            label="Gutschriften für Joker erzeugen",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiviert, Gutschriften werden automatisch für jeden Joker erzeugt. "
            "Das passiert an dem Tag wo die jeweiligen Joker nicht mehr abgesagt werden können.",
            category=ParameterCategory.JOKERS,
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.JOKERS_SOLIDARITY_CONTRIBUTION_PRODUCT_TYPE,
            label="Produkttyp für Solidarbeitrag bei Jokern",
            datatype=TapirParameterDatatype.STRING,
            initial_value=NO_SOLIDARITY_CONTRIBUTION_IN_JOKER_CREDITS,
            description="Wenn ein Produkttyp ausgewählt ist, wird der Solidarbeitrag des Mitglieds in der Joker-Gutschrift erstattet, "
            "falls das Mitglied einen Vertrag für diesen Produkttyp hat und dieser in der Joker-Woche geliefert wird. "
            "Der Solidarbeitrag zählt einmal pro Mitglied, unabhängig von der Anzahl der Anteile. "
            "Berechnung: monatlicher Solidarbeitrag × 12 ÷ Wochen im Jahr, bei 14-täglicher Lieferung × 2, bei 4-wöchentlicher Lieferung × 4.",
            category=ParameterCategory.JOKERS,
            order_priority=order_priority,
            meta=ParameterMeta(
                options_callable=lambda cache: [
                    (
                        NO_SOLIDARITY_CONTRIBUTION_IN_JOKER_CREDITS,
                        "Kein Solidarbeitrag",
                    )
                ]
                + [
                    (product_type.id, product_type.name)
                    for product_type in ProductType.objects.filter(
                        is_affected_by_jokers=True
                    )
                    .exclude(delivery_cycle=CUSTOM_CYCLE[0])
                    .order_by("name")
                ],
            ),
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            label="Lieferung-Spende Modus",
            datatype=TapirParameterDatatype.STRING,
            initial_value=DELIVERY_DONATION_MODE_DISABLED,
            description="Ob die Mitglieder einzelne Lieferungen spenden dürfen",
            category=ParameterCategory.JOKERS,
            order_priority=order_priority,
            meta=ParameterMeta(
                options=DELIVERY_DONATION_MODE_OPTIONS,
            ),
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
            label="Lieferung-Spende werden an diese Abholort versetzt",
            datatype=TapirParameterDatatype.STRING,
            initial_value=DELIVERY_DONATION_DONT_FORWARD_TO_PICKUP_LOCATION,
            description="Wenn eine Station ausgewählte ist werden die gespendete Lieferungen in der Kommissionierliste zu die ausgewählte Station versetzt."
            "<br />Die ausgewählte Station steht Mitglieder nicht mehr zu Verfügung, z.B. taucht sie nicht mehr im BestellWizard oder Mitgleiderbereich auf."
            "<br />Wenn keine Station ausgewählt ist tauchen gespendete Lieferungen in der Kommissionierliste gar nicht auf.",
            category=ParameterCategory.JOKERS,
            order_priority=order_priority,
            meta=ParameterMeta(
                options_callable=lambda cache: [
                    (
                        DELIVERY_DONATION_DONT_FORWARD_TO_PICKUP_LOCATION,
                        "Keine Versetzung",
                    )
                ]
                + [
                    (pickup_location.id, pickup_location.name)
                    for pickup_location in PickupLocation.objects.order_by("name")
                ],
            ),
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.EXPLANATION_TEXT_FOR_JOKERS_AND_DONATIONS,
            label="Erklärungstext zu Joker und/oder Spende",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Standard Erklärungstext zu Joker und Spende, in der Konfig anzupassen unter 'Erklärungstext zu Joker und/oder Spende'",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.JOKERS,
            order_priority=order_priority,
            meta=ParameterMeta(textarea=True),
        )
        order_priority -= 1
