from tapir.configuration.models import (
    TapirParameterDatatype,
    TapirParameterDefinitionImporter,
)
from tapir.configuration.parameter import parameter_definition


class ParameterCategory:
    SITE = "Standort"
    COOP = "Genossenschaft"
    CHICKEN = "Hühneranteile"
    BESTELLCOOP = "BestellCoop"
    HARVEST = "Ernteanteile"


class Parameter:
    SITE_NAME = "wirgarten.site.name"
    SITE_EMAIL = "wirgarten.site.email"
    SITE_PRIVACY_LINK = "wirgarten.site.privacy_link"
    COOP_MIN_SHARES = "wirgarten.coop.min_shares"
    COOP_SHARE_PRICE = "wirgarten.coop.share_price"
    COOP_STATUTE_LINK = "wirgarten.coop.statute_link"
    COOP_INFO_LINK = "wirgarten.coop.info_link"
    CHICKEN_MAX_SHARES = "wirgarten.chicken.max_shares"
    BESTELLCOOP_PRICE = "wirgarten.bestellcoop.price"
    HARVEST_NEGATIVE_SOLIPRICE_ENABLED = "wirgarten.harvest.negative_soliprice_enabled"


class ParameterDefinitions(TapirParameterDefinitionImporter):
    def import_definitions(self):
        parameter_definition(
            key=Parameter.SITE_NAME,
            datatype=TapirParameterDatatype.STRING,
            initial_value="WirGarten Lüneburg eG",
            description="Der Name des WirGarten Standorts. Beispiel: 'WirGarten Lüneburg eG'",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.SITE_EMAIL,
            datatype=TapirParameterDatatype.STRING,
            initial_value="lueneburg@wirgarten.com",
            description="Die Kontakt Email-Adresse des WirGarten Standorts. Beispiel: 'lueneburg@wirgarten.com'",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.SITE_PRIVACY_LINK,
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/datenschutzerklaerung",
            description="Der Link zur Datenschutzerklärung. Beispiel: 'https://lueneburg.wirgarten.com/datenschutzerklaerung'",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.COOP_MIN_SHARES,
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Die Mindestanzahl der Genossenschaftsanteile die ein neues Mitglied zeichnen muss.",
            category=ParameterCategory.COOP,
        )

        parameter_definition(
            key=Parameter.COOP_SHARE_PRICE,
            datatype=TapirParameterDatatype.DECIMAL,
            initial_value=50.0,
            description="Der Preis eines Genossenschaftsanteils in Euro.",
            category=ParameterCategory.COOP,
        )

        parameter_definition(
            key=Parameter.COOP_STATUTE_LINK,
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/satzung",
            description="Der Link zur Satzung der Genossenschaft.",
            category=ParameterCategory.COOP,
        )

        parameter_definition(
            key=Parameter.COOP_INFO_LINK,
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/genossenschaft/",
            description="Der Link zu weiteren Infos über die Genossenschaft/Mitgliedschaft.",
            category=ParameterCategory.COOP,
        )

        parameter_definition(
            key=Parameter.CHICKEN_MAX_SHARES,
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=5,
            description="Die maximale Anzahl Hühneranteile (pro Produkt) die pro Mitglied/Interessent gewählt werden kann.",
            category=ParameterCategory.CHICKEN,
        )

        parameter_definition(
            key=Parameter.BESTELLCOOP_PRICE,
            datatype=TapirParameterDatatype.DECIMAL,
            initial_value=3.0,
            description="Der monatliche Preis der BestellCoop Mitgliedschaft in Euro.",
            category=ParameterCategory.BESTELLCOOP,
        )

        parameter_definition(
            key=Parameter.HARVEST_NEGATIVE_SOLIPRICE_ENABLED,
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiv, dann ist es möglich bei der Auswahl der Ernteanteile einen niedrigeren Preis als den Richtpreis zu wählen.",
            category=ParameterCategory.HARVEST,
        )
