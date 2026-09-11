import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.wirgarten.constants import ParameterCategory, HTML_ALLOWED_TEXT
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsEmails:
    @classmethod
    def define_all_parameters_emails(cls, importer: ParameterDefinitions):
        order_priority = 100

        importer.parameter_definition(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES,
            label="Zusätzlich E-Mail-Adressen erlauben",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Ob Mitglieder im Mitgliederbereich zusätzliche Mail-Adressen eintragen können. "
            "Diese Adressen bekommen Kopie von alle Mails die an der Mitgliedshauptadresse versendet werden.",
            category=ParameterCategory.MAIL,
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.EXPLANATION_TEXT_EXTRA_MAIL_ADDRESSES,
            label="Erklärungstext zu zusätzliche Adressen",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""<p>
        Du kannst hier zusätzliche Mail-Adressen hinzufügen. Alle Mailings werden dann nach der Bestätigung der neuen Emailadresse auch an diese versendet. An die neue Email-Adresse wird ein Bestätigungslink versendet.
</p>""",
            description="Erklärungstext im Modal zu Zusätzliche Adressen im Mitgleiderbereich. "
            + HTML_ALLOWED_TEXT,
            category=ParameterCategory.MAIL,
            order_priority=order_priority,
            meta=ParameterMeta(
                textarea=True,
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
                ),
            ),
        )
        order_priority -= 1
