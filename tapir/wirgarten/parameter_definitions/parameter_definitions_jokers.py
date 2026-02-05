import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.deliveries.config import (
    DELIVERY_DONATION_MODE_DISABLED,
    DELIVERY_DONATION_MODE_OPTIONS,
    DELIVERY_DONATION_DONT_FORWARD_TO_PICKUP_LOCATION,
)
from tapir.wirgarten.constants import ParameterCategory, HTML_ALLOWED_TEXT
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsJokers:
    @classmethod
    def define_all_parameters_jokers(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.JOKERS_ENABLED,
            label="Joker-Feature einschalten",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Temporäre Liefer-Pausen pro Mitglied erlauben",
            category=ParameterCategory.JOKERS,
            order_priority=3,
        )

        importer.parameter_definition(
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            label="Lieferung-Spende Modus",
            datatype=TapirParameterDatatype.STRING,
            initial_value=DELIVERY_DONATION_MODE_DISABLED,
            description="Ob die Mitglieder einzelne Lieferungen spenden dürfen",
            category=ParameterCategory.JOKERS,
            order_priority=2,
            meta=ParameterMeta(
                options=DELIVERY_DONATION_MODE_OPTIONS,
            ),
        )

        importer.parameter_definition(
            key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
            label="Lieferung-Spende werden an diese Abholort versetzt",
            datatype=TapirParameterDatatype.STRING,
            initial_value=DELIVERY_DONATION_DONT_FORWARD_TO_PICKUP_LOCATION,
            description="Wenn eine Station ausgewählte ist werden die gespendete Lieferungen in der Kommissionierliste zu die ausgewählte Station versetzt."
            "<br />Die ausgewählte Station steht Mitglieder nicht mehr zu Verfügung, z.B. taucht sie nicht mehr im BestellWizard oder Mitgleiderbereich auf."
            "<br />Wenn keine Station ausgewählt ist tauchen gespendete Lieferungen in der Kommissionierliste gar nicht auf.",
            category=ParameterCategory.JOKERS,
            order_priority=1,
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

        importer.parameter_definition(
            key=ParameterKeys.EXPLANATION_TEXT_FOR_JOKERS_AND_DONATIONS,
            label="Erklärungstext zu Joker und/oder Spende",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Standard Erklärungstext zu Joker und Spende, in der Konfig anzupassen unter 'Erklärungstext zu Joker und/oder Spende'",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.JOKERS,
            order_priority=0,
            meta=ParameterMeta(textarea=True),
        )
