import typing

from django.conf import settings

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.core.config import (
    TEST_DATE_OVERRIDE_DISABLED,
    TEST_DATE_OVERRIDE_OPTIONS,
    TEST_DATE_OVERRIDE_MANUAL,
)
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.validators import validate_iso_datetime

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsTest:
    @classmethod
    def define_all_parameters_test(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.MEMBER_BYPASS_KEYCLOAK,
            label="TEMPORÄR: Umgehe Keycloak bei der Erstellung von Accounts",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Wenn aktiv, dann werden User nur in Tapir angelegt, ohne den Keycloak Account. Solange das der Fall ist, können sich diese User nicht anmelden.",
            category=ParameterCategory.TEST,
            enabled=is_debug_instance(),
        )

        if getattr(settings, "DEBUG", False):
            importer.parameter_definition(
                key=ParameterKeys.TESTS_OVERRIDE_DATE_PRESET,
                label="Datum festlegen",
                datatype=TapirParameterDatatype.STRING,
                initial_value=TEST_DATE_OVERRIDE_DISABLED,
                description="Setzt die Datum und Uhrzeit die von Tapir benutzt wird.<br />"
                'Wenn "Manuell" eingetragen ist, "taucht nach speichern ein zweites Feld um eine beliebiges Datum zu setzen.<br />'
                'Wenn "Nicht festgelegt" eingetragen ist, werden die echte Datum und Uhrzeit verwendet.<br />'
                "Aktuell verwendetes Datum: {{now}}",
                category=ParameterCategory.TEST,
                order_priority=2,
                debug=True,
                meta=ParameterMeta(options=TEST_DATE_OVERRIDE_OPTIONS),
            )

            importer.parameter_definition(
                key=ParameterKeys.TESTS_OVERRIDE_DATE,
                label="Beliebiges Test-Datum",
                datatype=TapirParameterDatatype.STRING,
                initial_value="2025-04-01 09:30",
                description="Format: YYYY-MM-DD HH:MM.<br />"
                'Wird nur eingesetzt wenn der Parameter "Datum festlegen" gleich Oben zu "Manuell" gesetzt ist.',
                category=ParameterCategory.TEST,
                order_priority=1,
                debug=True,
                meta=ParameterMeta(
                    validators=[validate_iso_datetime],
                    show_only_when=lambda cache: get_parameter_value(
                        ParameterKeys.TESTS_OVERRIDE_DATE_PRESET, cache=cache
                    )
                    == TEST_DATE_OVERRIDE_MANUAL,
                ),
            )
