from importlib.resources import _

from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    EmailValidator,
    URLValidator,
)
from localflavor.generic.validators import IBANValidator, BICValidator

from tapir.configuration.models import (
    TapirParameterDatatype,
    TapirParameterDefinitionImporter,
)
from tapir.configuration.parameter import parameter_definition, ParameterMeta
from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.models import ProductType
from tapir.wirgarten.validators import validate_format_string, validate_html

OPTIONS_WEEKDAYS = [
    (0, _("Montag")),
    (1, _("Dienstag")),
    (2, _("Mittwoch")),
    (3, _("Donnerstag")),
    (4, _("Freitag")),
    (5, _("Samstag")),
    (6, _("Sonntag")),
]

PREFIX = "wirgarten"


class ParameterCategory:
    SITE = "Standort"
    COOP = "Genossenschaft"
    ADDITIONAL_SHARES = "Zusatzabos"
    HARVEST = "Ernteanteile"
    SUPPLIER_LIST = "Lieferantenliste"
    PICK_LIST = "Kommissionierliste"
    PAYMENT = "Zahlungen"
    DELIVERY = "Lieferung"
    MEMBER_DASHBOARD = "Mitgliederbereich"


class Parameter:
    SITE_NAME = f"{PREFIX}.site.name"
    SITE_STREET = f"{PREFIX}.site.street"
    SITE_CITY = f"{PREFIX}.site.city"
    SITE_EMAIL = f"{PREFIX}.site.email"
    SITE_ADMIN_EMAIL = f"{PREFIX}.site.admin_email"
    SITE_PRIVACY_LINK = f"{PREFIX}.site.privacy_link"
    COOP_MIN_SHARES = f"{PREFIX}.coop.min_shares"
    COOP_STATUTE_LINK = f"{PREFIX}.coop.statute_link"
    COOP_INFO_LINK = f"{PREFIX}.coop.info_link"
    COOP_BASE_PRODUCT_TYPE = f"{PREFIX}.coop.base_product_type"
    COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES = f"{PREFIX}.coop.shares_independent"
    CHICKEN_MAX_SHARES = f"{PREFIX}.chicken.max_shares"
    CHICKEN_SHARES_SUBSCRIBABLE = f"{PREFIX}.chicken.is_subscribable"
    BESTELLCOOP_SUBSCRIBABLE = f"{PREFIX}.bestellcoop.is_subscribable"
    HARVEST_NEGATIVE_SOLIPRICE_ENABLED = f"{PREFIX}.harvest.negative_soliprice_enabled"
    HARVEST_SHARES_SUBSCRIBABLE = f"{PREFIX}.harvest.harvest_shares_subscribable"
    SUPPLIER_LIST_PRODUCT_TYPES = f"{PREFIX}.supplier_list.product_types"
    SUPPLIER_LIST_SEND_ADMIN_EMAIL = f"{PREFIX}.supplier_list.admin_email_enabled"
    PICK_LIST_SEND_ADMIN_EMAIL = f"{PREFIX}.pick_list.admin_email_enabled"
    PICK_LIST_PRODUCT_TYPES = f"{PREFIX}.pick_list.product_types"
    PAYMENT_DUE_DAY = f"{PREFIX}.payment.due_date"
    PAYMENT_IBAN = f"{PREFIX}.payment.iban"
    PAYMENT_BIC = f"{PREFIX}.payment.bic"
    PAYMENT_CREDITOR_ID = f"{PREFIX}.payment.creditor_id"
    DELIVERY_DAY = f"{PREFIX}.delivery.weekday"
    MEMBER_RENEWAL_ALERT_UNKOWN_HEADER = (
        f"{PREFIX}.member.dashboard.renewal_alert.unkown.header"
    )
    MEMBER_RENEWAL_ALERT_UNKOWN_CONTENT = (
        f"{PREFIX}.member.dashboard.renewal_alert.unkown.content"
    )
    MEMBER_RENEWAL_ALERT_CANCELLED_HEADER = (
        f"{PREFIX}.member.dashboard.renewal_alert.cancelled.header"
    )
    MEMBER_RENEWAL_ALERT_CANCELLED_CONTENT = (
        f"{PREFIX}.member.dashboard.renewal_alert.cancelled.content"
    )
    MEMBER_RENEWAL_ALERT_RENEWED_HEADER = (
        f"{PREFIX}.member.dashboard.renewal_alert.renewed.header"
    )
    MEMBER_RENEWAL_ALERT_RENEWED_CONTENT = (
        f"{PREFIX}.member.dashboard.renewal_alert.renewed.content"
    )


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
            meta=ParameterMeta(validators=[EmailValidator()]),
        )

        parameter_definition(
            key=Parameter.SITE_ADMIN_EMAIL,
            label="Admin Email",
            datatype=TapirParameterDatatype.STRING,
            initial_value="tapiradmin@wirgarten.com",
            description="Die Admin Email-Adresse des WirGarten Standorts. Beispiel: 'tapiradmin@wirgarten.com'",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[EmailValidator()]),
        )

        parameter_definition(
            key=Parameter.SITE_PRIVACY_LINK,
            label="Link zur Datenschutzerklärung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/datenschutzerklaerung",
            description="Der Link zur Datenschutzerklärung. Beispiel: 'https://lueneburg.wirgarten.com/datenschutzerklaerung'",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

        parameter_definition(
            key=Parameter.COOP_MIN_SHARES,
            label="Mindestanzahl Genossenschaftsanteile",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Die Mindestanzahl der Genossenschaftsanteile die ein neues Mitglied zeichnen muss.",
            category=ParameterCategory.COOP,
            order_priority=1000,
            meta=ParameterMeta(validators=[MinValueValidator(limit_value=0)]),
        )

        parameter_definition(
            key=Parameter.COOP_STATUTE_LINK,
            label="Link zur Satzung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/satzung",
            description="Der Link zur Satzung der Genossenschaft.",
            category=ParameterCategory.COOP,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

        parameter_definition(
            key=Parameter.COOP_INFO_LINK,
            label="Link zu weiteren Infos über die Genossenschaft",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/genossenschaft/",
            description="Der Link zu weiteren Infos über die Genossenschaft/Mitgliedschaft.",
            category=ParameterCategory.COOP,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

        parameter_definition(
            key=Parameter.CHICKEN_MAX_SHARES,
            label="Maximale Anzahl Hühneranteile pro Mitglied",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=5,
            description="Die maximale Anzahl Hühneranteile (pro Variante) die pro Mitglied/Interessent gewählt werden kann.",
            category=ParameterCategory.ADDITIONAL_SHARES,
        )

        parameter_definition(
            key=Parameter.HARVEST_NEGATIVE_SOLIPRICE_ENABLED,
            label="Solidarpreise möglich",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Aktiviert oder deaktiviert niedrigere Preise für Ernteanteile oder aktiviert die automatische Berechnung.",
            category=ParameterCategory.HARVEST,
            meta=ParameterMeta(
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
                ]
            ),
        )

        parameter_definition(
            key=Parameter.SUPPLIER_LIST_PRODUCT_TYPES,
            label="Produkte für Lieferantenlisten",
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
            key=Parameter.PICK_LIST_PRODUCT_TYPES,
            label="Produkte für Kommisionierliste",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ernteanteile",
            description="Komma-separierte Liste der Zusatzabos für die eine Kommissionierliste erzeugt werden soll.",
            category=ParameterCategory.PICK_LIST,
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
            meta=ParameterMeta(
                validators=[
                    MinValueValidator(limit_value=1),
                    MaxValueValidator(limit_value=31),
                ]
            ),
        )

        parameter_definition(
            key=Parameter.PAYMENT_IBAN,
            label="Empfänger IBAN",
            datatype=TapirParameterDatatype.STRING,
            initial_value="DE60240603002801881800",
            description="IBAN des Empfänger Kontos für Beitragszahlungen.",
            category=ParameterCategory.PAYMENT,
            order_priority=1000,
            meta=ParameterMeta(validators=[IBANValidator()]),
        )

        parameter_definition(
            key=Parameter.PAYMENT_BIC,
            label="Empfänger BIC",
            datatype=TapirParameterDatatype.STRING,
            initial_value="GENODEF1NBU",
            description="BIC des Empfänger Kontos für Beitragszahlungen.",
            category=ParameterCategory.PAYMENT,
            order_priority=900,
            meta=ParameterMeta(validators=[BICValidator()]),
        )

        parameter_definition(
            key=Parameter.PAYMENT_CREDITOR_ID,
            label="Gläubiger-ID",
            datatype=TapirParameterDatatype.STRING,
            initial_value="DE98ZZZ00001996599",
            description="Die Gläubiger-ID der Genossenschaft.",
            category=ParameterCategory.PAYMENT,
            order_priority=800,
        )

        # FIXME: obsolete
        parameter_definition(
            key=Parameter.DELIVERY_DAY,
            label="Wochentag an dem Ware geliefert wird",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Der Wochentag an dem die Ware zum Abholort geliefert wird.",
            category=ParameterCategory.DELIVERY,
            meta=ParameterMeta(options=OPTIONS_WEEKDAYS),
        )

        parameter_definition(
            key=Parameter.HARVEST_SHARES_SUBSCRIBABLE,
            label="Ernteanteile zeichenbar",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Wenn aktiv, dann sind Ernteateile von Mitgliedern zeichenbar.",
            category=ParameterCategory.HARVEST,
            meta=ParameterMeta(
                options=[
                    (2, "Automatik (zeichenbar abhängig von Kapaziät)"),
                    # (1, "zeichenbar"),
                    (0, "nicht zeichenbar"),
                ]
            ),
            order_priority=1000,
        )

        parameter_definition(
            key=Parameter.CHICKEN_SHARES_SUBSCRIBABLE,
            label="Hühneranteile zeichenbar",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Wenn aktiv, dann sind Hühneranteile von Mitgliedern zeichenbar.",
            category=ParameterCategory.ADDITIONAL_SHARES,
            meta=ParameterMeta(
                options=[
                    (2, "Automatik (zeichenbar abhängig von Kapazität)"),
                    # (1, "zeichenbar"),
                    (0, "nicht zeichenbar"),
                ]
            ),
        )

        parameter_definition(
            key=Parameter.BESTELLCOOP_SUBSCRIBABLE,
            label="BestellCoop Mitgliedschaft möglich",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Wenn aktiv, dann können neue BestellCoop Mitgliedschaften gebucht werden.",
            category=ParameterCategory.ADDITIONAL_SHARES,
            meta=ParameterMeta(
                options=[
                    (2, "Automatik (möglich abhängig von Kapaziät)"),
                    # (1, "zeichenbar"),
                    (0, "keine Anmeldung möglich"),
                ]
            ),
        )

        parameter_definition(
            key=Parameter.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES,
            label="Genossenschaftsanteile separat von Ernteanteilen zeichenbar",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Genossenschaftsanteile sind vom Mitglied separat von Ernteanteilen zeichenbar.",
            category=ParameterCategory.COOP,
            meta=ParameterMeta(
                options=[
                    (True, "separat zeichenbar"),
                    (False, "nicht separat zeichenbar"),
                ]
            ),
            order_priority=800,
        )

        MEMBER_RENEWAL_ALERT_VARS = [
            "member",
            "contract_end_date",
            "next_period_start_date",
            "next_period_end_date",
        ]

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_UNKOWN_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Mitglied hat weder verlängert noch gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{member.first_name}, dein Ernteanteil läuft bald aus!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, sofern das Mitglied seine Verträge weder verlängert noch explizit gekündigt hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=1000,
            meta=ParameterMeta(
                validators=[
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS)
                ]
            ),
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_UNKOWN_CONTENT,
            label="Text: Hinweis zur Vertragsverlängerung -> Mitglied hat weder verlängert noch gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Als <strong>bestehendes Mitglied</strong> hast du <strong>Vorrang</strong> beim Zeichnen von Ernteanteilen und Zusatzabos. Ab sofort kannst du deine Verträge für die <strong>nächste Saison</strong> verlängern.<br/><small>Andernfalls enden deine Verträge automatisch am {contract_end_date}.</small>""",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, sofern das Mitglied seine Verträge weder verlängert noch explizit gekündigt hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=900,
            meta=ParameterMeta(
                validators=[
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS)
                ]
            ),
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_CANCELLED_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Mitglied hat explizit gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schade, dass du gehst {member.first_name}!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge explizit zum Ende der Saison gekündigt hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=800,
            meta=ParameterMeta(
                validators=[
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS)
                ]
            ),
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_CANCELLED_CONTENT,
            label="Text: Hinweis zur Vertragsverlängerung -> Mitglied hat explizit gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Du wolltest keine neuen Ernteanteile für den Zeitraum <strong>{next_period.start_date} - {next_period.end_date}</strong> zeichnen. Hast du es dir anders überlegt? Dann verlängere jetzt hier deinen Erntevertrag.""",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge explizit zum Ende der Saison gekündigt hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=700,
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_RENEWED_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Mitglied hat Verträge verlängert",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schön, dass du dabei bleibst {member.first_name}!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge für die nächste Saison verlängert hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=600,
            meta=ParameterMeta(
                validators=[
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS)
                ]
            ),
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_RENEWED_CONTENT,
            label="Text: Hinweis zur Vertragsverlängerung -> Mitglied hat Verträge verlängert",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine Verträge wurden verlängert vom <strong>{next_period_start_date} - {next_period_end_date}</strong>.",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge für die nächste Saison verlängert hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=500,
            meta=ParameterMeta(
                validators=[
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS),
                    validate_html,
                ]
            ),
        )

        parameter_definition(
            key=Parameter.COOP_BASE_PRODUCT_TYPE,
            label="Basis Produkttyp",
            datatype=TapirParameterDatatype.STRING,
            initial_value=ProductType.objects.get(name=ProductTypes.HARVEST_SHARES).id,
            description="Der Basis Produkttyp. Andere Produkte können nicht bestellt werden, ohne einen Vertrag für den Basis Produkttypen.",
            category=ParameterCategory.COOP,
            meta=ParameterMeta(
                options=map(lambda x: (x.id, x.name), ProductType.objects.all())
            ),
        )
