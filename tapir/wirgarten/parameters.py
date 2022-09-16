from enum import Enum

from tapir.configuration.models import (
    ParameterDatatype,
)
from tapir.configuration.parameter import parameter_definition


class ParameterWirgarten(Enum):
    SITE_NAME = "wirgarten.site.name"
    SITE_EMAIL = "wirgarten.site.email"
    SITE_PRIVACY_LINK = "wirgarten.site.privacy_link"
    COOP_MIN_SHARES = "wirgarten.coop.min_shares"


def load_params():
    parameter_definition(
        key=ParameterWirgarten.SITE_NAME,
        datatype=ParameterDatatype.STRING,
        initial_value="WirGarten Lüneburg eG",
        description="Der Name des WirGarten Standorts. Beispiel: 'WirGarten Lüneburg eG'",
        category="Standort",
    )

    parameter_definition(
        key=ParameterWirgarten.SITE_EMAIL,
        datatype=ParameterDatatype.STRING,
        initial_value="lueneburg@wirgarten.com",
        description="Die Kontakt Email-Adresse des WirGarten Standorts. Beispiel: 'lueneburg@wirgarten.com'",
        category="Standort",
    )

    parameter_definition(
        key=ParameterWirgarten.SITE_PRIVACY_LINK,
        datatype=ParameterDatatype.STRING,
        initial_value="https://lueneburg.wirgarten.com/datenschutzerklaerung",
        description="Der Link zur Datenschutzerklärung. Beispiel: 'https://lueneburg.wirgarten.com/datenschutzerklaerung'",
        category="Standort",
    )

    parameter_definition(
        key=ParameterWirgarten.COOP_MIN_SHARES,
        datatype=ParameterDatatype.INTEGER,
        initial_value="2",
        description="Die Mindestanzahl der Genossenschaftsanteile die ein neues Mitglied zeichnen muss.",
        category="Genossenschaft",
    )
