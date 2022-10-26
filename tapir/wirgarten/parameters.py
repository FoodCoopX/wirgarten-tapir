import datetime

from tapir.configuration.models import (
    TapirParameterDatatype,
    TapirParameterDefinitionImporter,
)
from tapir.configuration.parameter import parameter_definition

OPTIONS_WEEKDAYS = [
    (0, "Montag"),
    (1, "Dienstag"),
    (2, "Mittwoch"),
    (3, "Donnerstag"),
    (4, "Freitag"),
    (5, "Samstag"),
    (6, "Sonntag"),
]

PREFIX = "wirgarten"


class ParameterCategory:
    SITE = "Standort"
    COOP = "Genossenschaft"
    CHICKEN = "Hühneranteile"
    BESTELLCOOP = "BestellCoop"
    HARVEST = "Ernteanteile"
    SUPPLIER_LIST = "Lieferantenliste"
    PICK_LIST = "Kommissionierliste"
    PAYMENT = "Zahlungen"
    DELIVERY = "Lieferung"


class Parameter:
    SITE_NAME = f"{PREFIX}.site.name"
    SITE_STREET = f"{PREFIX}.site.street"
    SITE_CITY = f"{PREFIX}.site.city"
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
    HARVEST_SHARES_SUBSCRIBABLE = f"{PREFIX}.harvest.harvest_shares_subscribable"
    SUPPLIER_LIST_PRODUCT_TYPES = f"{PREFIX}.supplier_list.product_types"
    SUPPLIER_LIST_SEND_ADMIN_EMAIL = f"{PREFIX}.supplier_list.admin_email_enabled"
    PICK_LIST_SEND_ADMIN_EMAIL = f"{PREFIX}.pick_list.admin_email_enabled"
    PAYMENT_DUE_DAY = f"{PREFIX}.payment.due_date"
    PAYMENT_IBAN = f"{PREFIX}.payment.iban"
    PAYMENT_BIC = f"{PREFIX}.payment.bic"
    PAYMENT_CREDITOR_ID = f"{PREFIX}.payment.creditor_id"
    DELIVERY_DAY = f"{PREFIX}.delivery.weekday"


class ParameterDefinitions(TapirParameterDefinitionImporter):
    def import_definitions(self):
        parameter_definition(
            key=Parameter.SITE_NAME,
            label="Standort Name",
            datatype=TapirParameterDatatype.STRING,
            initial_value="WirGarten Lüneburg eG",
            description="Der Name des WirGarten Standorts. Beispiel: 'WirGarten Lüneburg eG'",
            category=ParameterCategory.SITE,
            order_priority=1000,
        )

        parameter_definition(
            key=Parameter.SITE_STREET,
            label="Straße u. Hausnummer",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Vögelser Str. 25",
            description="Die Straße und Hausnummer des WirGarten Standorts. Beispiel: 'Vögelser Str. 25'",
            category=ParameterCategory.SITE,
            order_priority=900,
        )

        parameter_definition(
            key=Parameter.SITE_CITY,
            label="Postleitzahl u. Ort",
            datatype=TapirParameterDatatype.STRING,
            initial_value="21339 Lüneburg",
            description="Die PLZ und Ort des WirGarten Standorts. Beispiel: '21339 Lüneburg'",
            category=ParameterCategory.SITE,
            order_priority=800,
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
            order_priority=1000,
        )

        parameter_definition(
            key=Parameter.COOP_SHARE_PRICE,
            label="Preis für einen Genossenschaftsanteil",
            datatype=TapirParameterDatatype.DECIMAL,
            initial_value=50.0,
            description="Der Preis eines Genossenschaftsanteils in Euro.",
            category=ParameterCategory.COOP,
            order_priority=900,
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
            label="Solidarpreise möglich",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Aktiviert oder deaktiviert niedrigere Preise für Ernteanteile oder aktiviert die automatische Berechnung.",
            category=ParameterCategory.HARVEST,
            options=[
                (
                    0,
                    "Nur positive Solidarpreise möglich (Mitglieder können keinen niedrigeren Preis wählen)",
                ),
                (
                    1,
                    "Negative Solidarpreise möglich (Mitglieder können einen niedrigeren Preis wählen)",
                ),
                (
                    2,
                    "Automatische Berechnung (niedrigere Preise sind möglich, wenn genügend Mitglieder mehr zahlen)",
                ),
            ],
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

        parameter_definition(
            key=Parameter.PAYMENT_DUE_DAY,
            label="Fälligkeitsdatum der Beitragszahlungen (Tag des Monats)",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=15,
            description="Der Tag im Monat an dem Beitragszahlungen für Abonnements fällig sind.",
            category=ParameterCategory.PAYMENT,
        )

        parameter_definition(
            key=Parameter.PAYMENT_IBAN,
            label="Empfänger IBAN",
            datatype=TapirParameterDatatype.STRING,
            initial_value="DE60 2406 0300 2801 8818 00",
            description="IBAN des Empfänger Kontos für Beitragszahlungen.",
            category=ParameterCategory.PAYMENT,
            order_priority=1000,
        )

        parameter_definition(
            key=Parameter.PAYMENT_BIC,
            label="Empfänger BIC",
            datatype=TapirParameterDatatype.STRING,
            initial_value="GENODEF1NBU",
            description="BIC des Empfänger Kontos für Beitragszahlungen.",
            category=ParameterCategory.PAYMENT,
            order_priority=900,
        )

        parameter_definition(
            key=Parameter.PAYMENT_CREDITOR_ID,
            label="Gläubiger-ID",
            datatype=TapirParameterDatatype.STRING,
            initial_value="TODO",
            description="Die Gläubiger-ID der Genossenschaft.",
            category=ParameterCategory.PAYMENT,
            order_priority=800,
        )

        parameter_definition(
            key=Parameter.DELIVERY_DAY,
            label="Wochentag an dem Ware geliefert wird",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Der Wochentag an dem die Ware zum Abholort geliefert wird.",
            category=ParameterCategory.DELIVERY,
            options=OPTIONS_WEEKDAYS,
        )

        parameter_definition(
            key=Parameter.HARVEST_SHARES_SUBSCRIBABLE,
            label="Ernteanteile zeichenbar",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=1,
            description="Wenn aktiv, dann sind Enteateile von Mitgliedern zeichenbar.",
            category=ParameterCategory.HARVEST,
            options=[
                # (2, "Automatik"), # TODO: implement automatism logic
                (1, "zeichenbar"),
                (0, "nicht zeichenbar"),
            ],
            order_priority=1000,
        )
