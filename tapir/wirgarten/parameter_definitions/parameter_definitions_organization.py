import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.core.config import (
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_OPTIONS,
    THEME_OPTIONS,
    THEME_TEST,
)
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_cooperative

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsOrganization:
    @classmethod
    def define_all_parameters_organization(cls, importer: ParameterDefinitions):
        parameter_order = 100

        importer.parameter_definition(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS,
            label="Rechtsform der Organisation",
            datatype=TapirParameterDatatype.STRING,
            initial_value=LEGAL_STATUS_COOPERATIVE,
            description="",
            category=ParameterCategory.ORGANIZATION,
            order_priority=parameter_order,
            meta=ParameterMeta(options=LEGAL_STATUS_OPTIONS),
            enabled=is_debug_instance(),
        )
        parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.ORGANISATION_THEME,
            label="Theme",
            datatype=TapirParameterDatatype.STRING,
            initial_value=THEME_TEST,
            description="",
            category=ParameterCategory.ORGANIZATION,
            order_priority=parameter_order,
            meta=ParameterMeta(options=THEME_OPTIONS),
        )
        parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.ORGANISATION_QUESTIONAIRE_SOURCES,
            label="Vertriebskanäle",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Social Media, Zeitung, Suchmaschine",
            description="Welche Kanäle zur Auswahl stehen am Ende der BestellWizard, als Komma-getrennte Liste. Beispiel: 'Social Media, Zeitung, Suchmaschine'",
            category=ParameterCategory.ORGANIZATION,
            order_priority=parameter_order,
        )
        parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
            label="Studenten dürfen ohne Genossenschaft-Anteile Produkte bestellen",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiviert kommt ein extra Checkbox im Bestellwizard, die wenn angekreuzt erlaubt Studentinnen eine Bestellung abzuschliessen ohne Genossenschaft-Anteile.",
            category=ParameterCategory.ORGANIZATION,
            order_priority=parameter_order,
            meta=ParameterMeta(show_only_when=legal_status_is_cooperative),
        )
        parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.LABEL_STUDENT_CHECKBOX,
            label="Label für die Checkbox 'Student*in'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ich bin Student*in und kann keine Genossenschaftsanteile zeichnen",
            description="Text neben der Checkbox zu Studentenstatus im Bestellwizard und Mitgliederbereich",
            category=ParameterCategory.ORGANIZATION,
            order_priority=parameter_order,
            meta=ParameterMeta(
                show_only_when=lambda cache: legal_status_is_cooperative(cache)
                and get_parameter_value(
                    key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
                    cache=cache,
                )
            ),
        )
        parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.STUDENT_CHECKBOX_EXPLANATION_TEXT,
            label="Erklärungstext zu Student-Status im BestellWizard",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Die Immatrikulationsbescheinigung muss per Mail an {{kontakt_mail}} gesendet werden.",
            description="",
            category=ParameterCategory.ORGANIZATION,
            order_priority=parameter_order,
            meta=ParameterMeta(
                show_only_when=lambda cache: legal_status_is_cooperative(cache)
                and get_parameter_value(
                    key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
                    cache=cache,
                ),
                vars_hint=["kontakt_mail"],
            ),
        )
        parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP10_FLAG_STUDENT,
            label="Im BestellWizard bei der Zusammenfassung-Seite, Titel wenn kein Geno-Anteil gezeichnet weil Student",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Keine Mitgliedschaft in der Genossenschaft (Student)",
            description="",
            category=ParameterCategory.ORGANIZATION,
            order_priority=parameter_order,
            meta=ParameterMeta(
                show_only_when=lambda cache: legal_status_is_cooperative(cache)
                and get_parameter_value(
                    key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
                    cache=cache,
                )
            ),
        )
        parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP10_TEXT_STUDENT,
            label="Im BestellWizard bei der Zusammenfassung-Seite, Text wenn kein Geno-Anteil gezeichnet weil Student",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Keine Anteile gezeichnet da Student.",
            description="",
            category=ParameterCategory.ORGANIZATION,
            order_priority=parameter_order,
            meta=ParameterMeta(
                show_only_when=lambda cache: legal_status_is_cooperative(cache)
                and get_parameter_value(
                    key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
                    cache=cache,
                )
            ),
        )
        parameter_order -= 1
