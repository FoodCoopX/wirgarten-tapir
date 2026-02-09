import typing

from django.core.validators import EmailValidator, URLValidator

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsSite:
    @classmethod
    def define_all_parameters_site(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.SITE_NAME,
            label="Standort Name",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Standort Name",
            description="Der Name des Standorts. Beispiel: 'WirGarten Lüneburg eG'",
            category=ParameterCategory.SITE,
            order_priority=1000,
        )

        importer.parameter_definition(
            key=ParameterKeys.SITE_STREET,
            label="Straße u. Hausnummer",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Vögelser Str. 25",
            description="Die Straße und Hausnummer des Standorts. Beispiel: 'Vögelser Str. 25'",
            category=ParameterCategory.SITE,
            order_priority=900,
        )

        importer.parameter_definition(
            key=ParameterKeys.SITE_CITY,
            label="Postleitzahl u. Ort",
            datatype=TapirParameterDatatype.STRING,
            initial_value="12345 Stadtville",
            description="Die PLZ und Ort des Standorts. Beispiel: '21339 Lüneburg'",
            category=ParameterCategory.SITE,
            order_priority=800,
        )

        importer.parameter_definition(
            key=ParameterKeys.SITE_EMAIL,
            label="Kontakt Email-Adresse",
            datatype=TapirParameterDatatype.STRING,
            initial_value="contact@example.com",
            description="Die Kontakt Email-Adresse des Standorts. Beispiel: 'lueneburg@wirgarten.com'",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[EmailValidator()]),
        )

        importer.parameter_definition(
            key=ParameterKeys.SITE_ADMIN_EMAIL,
            label="Admin Email",
            datatype=TapirParameterDatatype.STRING,
            initial_value="admin@example.com",
            description="Die Admin Email-Adresse des Standorts. Beispiel: 'tapiradmin@wirgarten.com'",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[EmailValidator()]),
        )

        importer.parameter_definition(
            key=ParameterKeys.SITE_ADMIN_NAME,
            label="Admin/Ansprechpartner Name",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Max Mustermann",
            description="Der Name des Ansprechpartners für Mitglieder",
            category=ParameterCategory.SITE,
        )

        importer.parameter_definition(
            key=ParameterKeys.SITE_ADMIN_TELEPHONE,
            label="Admin/Ansprechpartner Telefonnummer",
            datatype=TapirParameterDatatype.STRING,
            initial_value="+49 176 34 45 81 48",
            description="Die Kontakttelefonnummer für Mitglieder",
            category=ParameterCategory.SITE,
        )

        importer.parameter_definition(
            key=ParameterKeys.SITE_ADMIN_IMAGE,
            label="Admin/Ansprechpartner Foto",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://placehold.net/avatar.svg",
            description="Ein Foto der Kontaktperson für Mitglieder",
            category=ParameterCategory.SITE,
        )

        importer.parameter_definition(
            key=ParameterKeys.SITE_PRIVACY_LINK,
            label="Link zur Datenschutzerklärung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://betrieb.de/datenschutzerklaerung",
            description="Der Link zur Datenschutzerklärung. Beispiel: 'https://lueneburg.wirgarten.com/datenschutzerklaerung'",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

        importer.parameter_definition(
            key=ParameterKeys.SITE_FAQ_LINK,
            label="Link zum Mitglieder-FAQ",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://betrieb.de/faq",
            description="Der Link zum FAQ für Mitglieder",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[URLValidator()]),
        )
