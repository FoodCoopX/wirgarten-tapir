from tapir.configuration.models import (
    TapirParameterDatatype,
    TapirParameterDefinitionImporter,
)
from tapir.configuration.parameter import parameter_definition

PREFIX = "wirgarten"


class ParameterCategory:
    SITE = "Standort"
    COOP = "Genossenschaft"
    CHICKEN = "Hühneranteile"
    BESTELLCOOP = "BestellCoop"
    HARVEST = "Ernteanteile"
    SUPPLIER_LIST = "Lieferantenliste"
    PICK_LIST = "Kommissionierliste"


class Parameter:
    SITE_NAME = f"{PREFIX}.site.name"
    SITE_EMAIL = f"{PREFIX}.site.email"
    SITE_ADMIN_EMAIL = f"{PREFIX}.site.admin_email"
    SITE_PRIVACY_LINK = f"{PREFIX}.site.privacy_link"
    COOP_MIN_SHARES = f"{PREFIX}.coop.min_shares"
    COOP_SHARE_PRICE = f"{PREFIX}.coop.share_price"
    COOP_STATUTE_LINK = f"{PREFIX}.coop.statute_link"
    COOP_INFO_LINK = f"{PREFIX}.coop.info_link"
    CHICKEN_MAX_SHARES = f"{PREFIX}.chicken.max_shares"
    BESTELLCOOP_PRICE = f"{PREFIX}.bestellcoop.price"
    HARVEST_NEGATIVE_SOLIPRICE_ENABLED = f"{PREFIX}.harvest.negative_soliprice_enabled"
    SUPPLIER_LIST_PRODUCT_TYPES = f"{PREFIX}.supplier_list.product_types"
    SUPPLIER_LIST_SEND_ADMIN_EMAIL = f"{PREFIX}.supplier_list.admin_email_enabled"
    PICK_LIST_SEND_ADMIN_EMAIL = f"{PREFIX}.pick_list.admin_email_enabled"


class ParameterDefinitions(TapirParameterDefinitionImporter):
    def import_definitions(self):
        parameter_definition(
            key=Parameter.SITE_NAME,
            label="Standort Name",
            datatype=TapirParameterDatatype.STRING,
            initial_value="WirGarten Lüneburg eG",
            description="Der Name des WirGarten Standorts. Beispiel: 'WirGarten Lüneburg eG'",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.SITE_EMAIL,
            label="Kontakt Email-Adresse",
            datatype=TapirParameterDatatype.STRING,
            initial_value="lueneburg@wirgarten.com",
            description="Die Kontakt Email-Adresse des WirGarten Standorts. Beispiel: 'lueneburg@wirgarten.com'",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.SITE_ADMIN_EMAIL,
            label="Admin Email",
            datatype=TapirParameterDatatype.STRING,
            initial_value="tapiradmin@wirgarten.com",
            description="Die Admin Email-Adresse des WirGarten Standorts. Beispiel: 'tapiradmin@wirgarten.com'",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.SITE_PRIVACY_LINK,
            label="Link zur Datenschutzerklärung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/datenschutzerklaerung",
            description="Der Link zur Datenschutzerklärung. Beispiel: 'https://lueneburg.wirgarten.com/datenschutzerklaerung'",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.COOP_MIN_SHARES,
            label="Mindestanzahl Genossenschaftsanteile",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Die Mindestanzahl der Genossenschaftsanteile die ein neues Mitglied zeichnen muss.",
            category=ParameterCategory.COOP,
        )

        parameter_definition(
            key=Parameter.COOP_SHARE_PRICE,
            label="Preis für einen Genossenschaftsanteil",
            datatype=TapirParameterDatatype.DECIMAL,
            initial_value=50.0,
            description="Der Preis eines Genossenschaftsanteils in Euro.",
            category=ParameterCategory.COOP,
        )

        parameter_definition(
            key=Parameter.COOP_STATUTE_LINK,
            label="Link zur Satzung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/satzung",
            description="Der Link zur Satzung der Genossenschaft.",
            category=ParameterCategory.COOP,
        )

        parameter_definition(
            key=Parameter.COOP_INFO_LINK,
            label="Link zu weiteren Infos über die Genossenschaft",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/genossenschaft/",
            description="Der Link zu weiteren Infos über die Genossenschaft/Mitgliedschaft.",
            category=ParameterCategory.COOP,
        )

        parameter_definition(
            key=Parameter.CHICKEN_MAX_SHARES,
            label="Maximale Anzahl Hühneranteile pro Mitglied",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=5,
            description="Die maximale Anzahl Hühneranteile (pro Produkt) die pro Mitglied/Interessent gewählt werden kann.",
            category=ParameterCategory.CHICKEN,
        )

        parameter_definition(
            key=Parameter.BESTELLCOOP_PRICE,
            label="Monatlicher Preis für BestellCoop Mitgliedschaft",
            datatype=TapirParameterDatatype.DECIMAL,
            initial_value=3.0,
            description="Der monatliche Preis der BestellCoop Mitgliedschaft in Euro.",
            category=ParameterCategory.BESTELLCOOP,
        )

        parameter_definition(
            key=Parameter.HARVEST_NEGATIVE_SOLIPRICE_ENABLED,
            label="Solipreise möglich",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiv, dann ist es möglich bei der Auswahl der Ernteanteile einen niedrigeren Preis als den Richtpreis zu wählen.",
            category=ParameterCategory.HARVEST,
        )

        parameter_definition(
            key=Parameter.SUPPLIER_LIST_PRODUCT_TYPES,
            label="Produkte für Lieferentenlisten",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Hühneranteile",
            description="Komma-separierte Liste der Zusatzabos für die eine Lieferantenliste erzeugt werden soll.",
            category=ParameterCategory.SUPPLIER_LIST,
        )

        parameter_definition(
            key=Parameter.SUPPLIER_LIST_SEND_ADMIN_EMAIL,
            label="Automatische Email an Admin",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiv, dann wird automatisch wöchentlich eine Email mit den Lieferantenlisten an den Admin versandt.",
            category=ParameterCategory.SUPPLIER_LIST,
        )

        parameter_definition(
            key=Parameter.PICK_LIST_SEND_ADMIN_EMAIL,
            label="Automatische Email an Admin",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiv, dann wird automatisch wöchentlich eine Email mit der Kommisionierliste an den Admin versandt.",
            category=ParameterCategory.PICK_LIST,
        )
