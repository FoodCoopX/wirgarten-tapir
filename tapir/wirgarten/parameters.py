from django.conf import settings
from django.core.validators import (
    EmailValidator,
    MaxValueValidator,
    MinValueValidator,
    URLValidator,
)
from django.utils.translation import gettext_lazy as _

from tapir.configuration.models import (
    TapirParameterDatatype,
    TapirParameterDefinitionImporter,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import (
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_OPTIONS,
    TEST_DATE_OVERRIDE_MANUAL,
    TEST_DATE_OVERRIDE_DISABLED,
    TEST_DATE_OVERRIDE_OPTIONS,
)
from tapir.pickup_locations.config import OPTIONS_PICKING_MODE, PICKING_MODE_SHARE
from tapir.subscriptions.config import (
    NOTICE_PERIOD_UNIT_MONTHS,
    NOTICE_PERIOD_UNIT_OPTIONS,
)
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import (
    legal_status_is_cooperative,
    legal_status_is_association,
)

OPTIONS_WEEKDAYS = [
    (0, _("Montag")),
    (1, _("Dienstag")),
    (2, _("Mittwoch")),
    (3, _("Donnerstag")),
    (4, _("Freitag")),
    (5, _("Samstag")),
    (6, _("Sonntag")),
]


class ParameterCategory:
    SITE = "Standort"
    BUSINESS = "{{legal_status}}"
    ADDITIONAL_SHARES = "Zusatzabos"
    HARVEST = "Ernteanteile"
    SUPPLIER_LIST = "Lieferantenliste"
    PICKING = "Kommissionierung"
    PAYMENT = "Zahlungen"
    DELIVERY = "Lieferung"
    MEMBER_DASHBOARD = "Mitgliederbereich"
    EMAIL = "Email"
    JOKERS = "Joker"
    SUBSCRIPTIONS = "Verträge"
    TEST = "Tests"
    ORGANIZATION = "Organisation"


class ParameterDefinitions(TapirParameterDefinitionImporter):
    def import_definitions(self):
        from tapir.configuration.parameter import ParameterMeta, parameter_definition
        from tapir.wirgarten.models import ProductType
        from tapir.wirgarten.validators import (
            validate_html,
            validate_iso_datetime,
            validate_base_product_type_exists,
        )
        from tapir.pickup_locations.services.basket_size_capacities_service import (
            BasketSizeCapacitiesService,
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL,
            label="Abholort-Änderung möglich bis",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=6,
            description="Bis zu welchem Wochentag kann ein Mitglied seinen Abholort ändern, um für die darauffolgede Woche den neuen Abholort zu nutzen? Es gilt der gewählte Tag bis 23:59 Uhr.",
            category=ParameterCategory.MEMBER_DASHBOARD,
            meta=ParameterMeta(options=OPTIONS_WEEKDAYS),
        )

        parameter_definition(
            key=ParameterKeys.SITE_NAME,
            label="Standort Name",
            datatype=TapirParameterDatatype.STRING,
            initial_value="WirGarten Lüneburg eG",
            description="Der Name des WirGarten Standorts. Beispiel: 'WirGarten Lüneburg eG'",
            category=ParameterCategory.SITE,
            order_priority=1000,
        )

        parameter_definition(
            key=ParameterKeys.SITE_STREET,
            label="Straße u. Hausnummer",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Vögelser Str. 25",
            description="Die Straße und Hausnummer des WirGarten Standorts. Beispiel: 'Vögelser Str. 25'",
            category=ParameterCategory.SITE,
            order_priority=900,
        )

        parameter_definition(
            key=ParameterKeys.SITE_CITY,
            label="Postleitzahl u. Ort",
            datatype=TapirParameterDatatype.STRING,
            initial_value="21339 Lüneburg",
            description="Die PLZ und Ort des WirGarten Standorts. Beispiel: '21339 Lüneburg'",
            category=ParameterCategory.SITE,
            order_priority=800,
        )

        parameter_definition(
            key=ParameterKeys.SITE_EMAIL,
            label="Kontakt Email-Adresse",
            datatype=TapirParameterDatatype.STRING,
            initial_value="lueneburg@wirgarten.com",
            description="Die Kontakt Email-Adresse des WirGarten Standorts. Beispiel: 'lueneburg@wirgarten.com'",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[EmailValidator()]),
        )

        parameter_definition(
            key=ParameterKeys.SITE_ADMIN_EMAIL,
            label="Admin Email",
            datatype=TapirParameterDatatype.STRING,
            initial_value="tapiradmin@wirgarten.com",
            description="Die Admin Email-Adresse des WirGarten Standorts. Beispiel: 'tapiradmin@wirgarten.com'",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[EmailValidator()]),
        )

        parameter_definition(
            key=ParameterKeys.SITE_ADMIN_NAME,
            label="Admin/Ansprechpartner Name",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Lukas Heidelberg",
            description="Der Name des Ansprechpartners für Mitglieder",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=ParameterKeys.SITE_ADMIN_TELEPHONE,
            label="Admin/Ansprechpartner Telefonnummer",
            datatype=TapirParameterDatatype.STRING,
            initial_value="+49 176 34 45 81 48",
            description="Die Kontakttelefonnummer für Mitglieder",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=ParameterKeys.SITE_ADMIN_IMAGE,
            label="Admin/Ansprechpartner Foto",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/wp-content/uploads/sites/4/2023/03/lukas-heidelberg-higher-res.jpg",
            description="Ein Foto der Kontaktperson für Mitglieder",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=ParameterKeys.SITE_PRIVACY_LINK,
            label="Link zur Datenschutzerklärung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/datenschutzerklaerung",
            description="Der Link zur Datenschutzerklärung. Beispiel: 'https://lueneburg.wirgarten.com/datenschutzerklaerung'",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

        parameter_definition(
            key=ParameterKeys.SITE_FAQ_LINK,
            label="Link zum Mitglieder-FAQ",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/faq",
            description="Der Link zum FAQ für Mitglieder",
            category=ParameterCategory.SITE,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

        parameter_definition(
            key=ParameterKeys.COOP_MIN_SHARES,
            label="Mindestanzahl Genossenschaftsanteile",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Die Mindestanzahl der Genossenschaftsanteile die ein neues Mitglied zeichnen muss.",
            category=ParameterCategory.BUSINESS,
            order_priority=1000,
            meta=ParameterMeta(
                validators=[MinValueValidator(limit_value=0)],
                show_only_when=legal_status_is_cooperative,
            ),
        )

        parameter_definition(
            key=ParameterKeys.COOP_STATUTE_LINK,
            label="Link zur Satzung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/satzung",
            description="Der Link zur Satzung des Betriebs.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

        parameter_definition(
            key=ParameterKeys.COOP_INFO_LINK,
            label="Link zu weiteren Infos über der Betrieb",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/genossenschaft/",
            description="Der Link zu weiteren Infos über der Betrieb.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(validators=[URLValidator()]),
        )

        parameter_definition(
            key=ParameterKeys.COOP_MEMBERSHIP_NOTICE_PERIOD,
            label="Kündigungsfrist für die Vereinsmitgliedschaft",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(show_only_when=legal_status_is_association),
            enabled=is_debug_instance(),
        )

        parameter_definition(
            key=ParameterKeys.COOP_MEMBERSHIP_NOTICE_PERIOD_UNIT,
            label="Einheit der Kündigungsfrist für die Vereinsmitgliedschaft",
            datatype=TapirParameterDatatype.STRING,
            initial_value=NOTICE_PERIOD_UNIT_MONTHS,
            description="Ob der Feld 'Kündigungsfrist für die Vereinsmitgliedschaft' Monate oder Wochen angibt",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(
                options=NOTICE_PERIOD_UNIT_OPTIONS,
                show_only_when=legal_status_is_association,
            ),
            enabled=is_debug_instance(),
        )

        parameter_definition(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED,
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
                        "Negative Solidarpreise möglich (Mitglieder können immer einen niedrigeren Preis wählen)",
                    ),
                    (
                        2,
                        "Automatische Berechnung (niedrigere Preise sind möglich, wenn genügend Mitglieder mehr zahlen)",
                    ),
                ]
            ),
        )

        parameter_definition(
            key=ParameterKeys.SUPPLIER_LIST_PRODUCT_TYPES,
            label="Produkte für Lieferantenlisten",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Hühneranteile",
            description="Komma-separierte Liste der Zusatzabos für die eine Lieferantenliste erzeugt werden soll.",
            category=ParameterCategory.SUPPLIER_LIST,
        )

        parameter_definition(
            key=ParameterKeys.SUPPLIER_LIST_SEND_ADMIN_EMAIL,
            label="Automatische Email an Admin",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiv, dann wird automatisch wöchentlich eine Email mit den Lieferantenlisten an den Admin versandt.",
            category=ParameterCategory.SUPPLIER_LIST,
        )

        parameter_definition(
            key=ParameterKeys.PICKING_PRODUCT_TYPES,
            label="Produkte für Kommisionierliste",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ernteanteile",
            description="Komma-separierte Liste der Zusatzabos für die eine Kommissionierliste erzeugt werden soll.",
            category=ParameterCategory.PICKING,
            order_priority=4,
        )

        parameter_definition(
            key=ParameterKeys.PICKING_SEND_ADMIN_EMAIL,
            label="Automatische Email an Admin",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiv, dann wird automatisch wöchentlich eine Email mit der Kommisionierliste an den Admin versandt.",
            category=ParameterCategory.PICKING,
            order_priority=5,
        )

        parameter_definition(
            key=ParameterKeys.PICKING_MODE,
            label="Kommissionierungsmodus",
            datatype=TapirParameterDatatype.STRING,
            initial_value=PICKING_MODE_SHARE,
            description="Ob Verteilstation-Kapazitäten nach Anteile oder Kisten berechnet werden",
            category=ParameterCategory.PICKING,
            order_priority=3,
            meta=ParameterMeta(options=OPTIONS_PICKING_MODE),
            enabled=is_debug_instance(),
        )

        parameter_definition(
            key=ParameterKeys.PICKING_BASKET_SIZES,
            label="Kistengrößen",
            datatype=TapirParameterDatatype.STRING,
            initial_value="kleine Kiste;normale Kiste;",
            description=f"Nur relevant beim Kommissionierungsmodus nach Kisten. Liste der Kistengrößen, mit ';' getrennt. Beispiel: 'kleine Kiste;normale Kiste;'",
            category=ParameterCategory.PICKING,
            order_priority=2,
            meta=ParameterMeta(
                validators=[BasketSizeCapacitiesService.validate_basket_sizes]
            ),
        )

        parameter_definition(
            key=ParameterKeys.PAYMENT_DUE_DAY,
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
            enabled=False,
        )

        parameter_definition(
            key=ParameterKeys.DELIVERY_DAY,
            label="Wochentag an dem Ware geliefert wird",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Der Wochentag an dem die Ware zum Abholort geliefert wird.",
            category=ParameterCategory.DELIVERY,
            meta=ParameterMeta(options=OPTIONS_WEEKDAYS),
        )

        parameter_definition(
            key=ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES,
            label="Genossenschaftsanteile separat von Ernteanteilen zeichenbar",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Genossenschaftsanteile sind vom Mitglied separat von Ernteanteilen zeichenbar.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(
                options=[
                    (True, "separat zeichenbar"),
                    (False, "nicht separat zeichenbar"),
                ],
                show_only_when=legal_status_is_cooperative,
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
            key=ParameterKeys.MEMBER_RENEWAL_ALERT_UNKOWN_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Mitglied hat weder verlängert noch gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{member.first_name}, dein Ernteanteil läuft bald aus!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, sofern das Mitglied seine Verträge weder verlängert noch explizit gekündigt hat (erscheint 3 Monate vor Beginn der nächsten Vertragsperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=801,
            meta=ParameterMeta(
                vars_hint=MEMBER_RENEWAL_ALERT_VARS,
            ),
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_RENEWAL_ALERT_UNKOWN_CONTENT,
            label="Text: Hinweis zur Vertragsverlängerung -> Mitglied hat weder verlängert noch gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Als <strong>bestehendes Mitglied</strong> hast du <strong>Vorrang</strong> beim Zeichnen von Ernteanteilen und Zusatzabos. Ab sofort kannst du deine Verträge für die <strong>nächste Saison</strong> verlängern.<br/><small>Andernfalls enden deine Verträge automatisch am {contract_end_date}.</small>""",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, sofern das Mitglied seine Verträge weder verlängert noch explizit gekündigt hat (erscheint 3 Monate vor Beginn der nächsten Vertragsperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=800,
            meta=ParameterMeta(
                vars_hint=MEMBER_RENEWAL_ALERT_VARS,
                validators=[
                    validate_html,
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_RENEWAL_ALERT_CANCELLED_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Mitglied hat explizit gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schade, dass du gehst {member.first_name}!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge explizit zum Ende der Saison gekündigt hat (erscheint 3 Monate vor Beginn der nächsten Vertragsperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=701,
            meta=ParameterMeta(
                vars_hint=MEMBER_RENEWAL_ALERT_VARS,
            ),
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_RENEWAL_ALERT_CANCELLED_CONTENT,
            label="Text: Hinweis zur Vertragsverlängerung -> Mitglied hat explizit gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Du wolltest keine neuen Ernteanteile für den Zeitraum <strong>{next_period_start_date} - {next_period_end_date}</strong> zeichnen. Hast du es dir anders überlegt? Dann verlängere jetzt hier deinen Erntevertrag.""",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge explizit zum Ende der Saison gekündigt hat (erscheint 3 Monate vor Beginn der nächsten Vertragsperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=700,
            meta=ParameterMeta(
                textarea=True,
                vars_hint=MEMBER_RENEWAL_ALERT_VARS,
                validators=[
                    validate_html,
                ],
            ),
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_RENEWAL_ALERT_RENEWED_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Mitglied hat Verträge verlängert",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schön, dass du dabei bleibst {member.first_name}!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge für die nächste Saison verlängert hat (erscheint 3 Monate vor Beginn der nächsten Vertragsperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=601,
            meta=ParameterMeta(
                vars_hint=MEMBER_RENEWAL_ALERT_VARS,
            ),
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_RENEWAL_ALERT_RENEWED_CONTENT,
            label="Text: Hinweis zur Vertragsverlängerung -> Mitglied hat Verträge verlängert",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine Verträge wurden verlängert vom <strong>{next_period_start_date} - {next_period_end_date}</strong>.",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge für die nächste Saison verlängert hat (erscheint 3 Monate vor Beginn der nächsten Vertragsperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=600,
            meta=ParameterMeta(
                vars_hint=MEMBER_RENEWAL_ALERT_VARS + ["contract_list"],
                validators=[
                    validate_html,
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_RENEWAL_ALERT_WAITLIST_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Keine Kapazität (Warteliste)",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Wir haben keine Ernteanteile mehr, {member.first_name}!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, wenn das Mitglied weder gekündigt noch verlängert hat, aber die Kapazität für Ernteanteile aufgebraucht ist (erscheint 3 Monate vor Beginn der nächsten Vertragsperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=501,
            meta=ParameterMeta(vars_hint=MEMBER_RENEWAL_ALERT_VARS),
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_RENEWAL_ALERT_WAITLIST_CONTENT,
            label="Text: Hinweis zur Vertragsverlängerung -> Keine Kapazität (Warteliste)",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine Verträge enden am <strong>{contract_end_date}</strong>. Leider gibt es keine freien Ernteanteile mehr für die nächste Anbausaison. Wenn du möchtest, benachrichtigen wir dich sobald wir wieder freie Ernteanteile haben.",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, wenn das Mitglied weder gekündigt noch verlängert hat, aber die Kapazität für Ernteanteile aufgebraucht ist (erscheint 3 Monate vor Beginn der nächsten Vertragsperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=500,
            meta=ParameterMeta(
                vars_hint=MEMBER_RENEWAL_ALERT_VARS,
                validators=[
                    validate_html,
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_CANCELLATION_REASON_CHOICES,
            label="Kündigungsgründe",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Menge (zu viel); Menge (zu wenig); Preis; Vielfalt; Qualität; Weg-/Umzug",
            description="Die Kündigungsgründe, die ein Mitglied bei der Kündigung auswählen kann. Die einzelnen Gründe werden durch Semikolon ';' getrennt angegeben.",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=400,
        )

        def get_default_product_type():
            if not hasattr(settings, "BASE_PRODUCT_NAME"):
                raise ValueError(
                    "BASE_PRODUCT_NAME is not set in tapir/wirgarten/settings/site.py"
                )

            default_product_type = ProductType.objects.filter(
                name=settings.BASE_PRODUCT_NAME
            )
            return (
                default_product_type.first().id
                if default_product_type.exists()
                else None
            )

        parameter_definition(
            key=ParameterKeys.COOP_BASE_PRODUCT_TYPE,
            label="Basis Produkttyp",
            datatype=TapirParameterDatatype.STRING,
            initial_value=get_default_product_type(),
            description="Der Basis Produkttyp. Andere Produkte können nicht bestellt werden, ohne einen Vertrag für den Basis Produkttypen.",
            category=ParameterCategory.BUSINESS,
            meta=ParameterMeta(
                options_callable=lambda: [
                    (product_type.id, product_type.name)
                    for product_type in ProductType.objects.all()
                ],
                validators=[validate_base_product_type_exists],
            ),
            enabled=is_debug_instance(),
        )

        DEFAULT_EMAIL_VARS = [
            "year_current",
            "year_next",
            "year_overnext",
            "admin_name",
            "admin_telephone",
            "admin_image",
            "site_name",
            "site_email",
        ]
        DEFAULT_EMAIL_MEMBER_VARS = ["member", "last_pickup_date"]

        parameter_definition(
            key=ParameterKeys.EMAIL_CANCELLATION_CONFIRMATION_SUBJECT,
            label="Betreff: Email 'Kündigungsbestätigung'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Kündigungsbestätigung",
            description="Betreff der Email, die bei Kündigung sofort an das Mitglied verschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=9999,
        )

        parameter_definition(
            key=ParameterKeys.EMAIL_CANCELLATION_CONFIRMATION_CONTENT,
            label="Inhalt: Email 'Kündigungsbestätigung'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Moin {member.first_name}, 

wir finden es sehr schade, dass Du deinen Erntevertrag kündigen willst, was wir dir hiermit zum <strong>{contract_end_date}</strong> bestätigen.

Wir freuen uns, wenn du uns mehr über deine Kündigungsgründe erzählen würdest. Das hilft uns immer zu schauen, ob und was wir verbessern können.
Für uns wäre es zudem sehr hilfreich, wenn Du dich mal in deinem Freundes- und Bekanntenkreis umhört, ob jemand deinen Ernteanteil eventuell übernehmen will, damit die Genossenschaft ausreichend finanziert ist. 
Du kannst deinen Erntevertrag dann auch schon vor Ablauf des Vertrages auf diese Person übertragen. Melde dich gerne einfach. 

Viele Grüße von {admin_name} aus deinem {site_name}""",
            description="Inhalt der Email (HTML), die bei Kündigung sofort an das Mitglied verschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=9998,
            meta=ParameterMeta(
                vars_hint=[
                    "contract_end_date",
                    "contract_list",
                ]
                + DEFAULT_EMAIL_MEMBER_VARS
                + DEFAULT_EMAIL_VARS,
                validators=[
                    validate_html,
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=ParameterKeys.EMAIL_NOT_RENEWED_CONFIRMATION_SUBJECT,
            label="Betreff: Email 'Bestätigung: Explizit nicht verlängert'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schade, dass du gehst!",
            description="Betreff der Email, die bei expliziter nicht-Verlängerung sofort an das Mitglied verschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=9979,
        )

        parameter_definition(
            key=ParameterKeys.EMAIL_NOT_RENEWED_CONFIRMATION_CONTENT,
            label="Inhalt: Email 'Bestätigung: Explizit nicht verlängert'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Liebe/r {member.first_name},

vielen Dank, dass du uns mitteilst, dass du deinen Ernteertrag nicht verlängern wirst - das hilft uns sehr bei der Planung! Aber trotzdem: Schade, dass Du gehst! Wir danken dir für dein Vertrauen und deine Unterstützung bis hierher!

Es wäre super, wenn Du deinen Freund:innen und Bekannten vom WirGarten erzählst. Denn unsere Genossenschaft kann nur weiter bestehen, wenn ausreichend Menschen den Betrieb und unsere Art der Landwirtschaft unterstützen. Vielen Dank dafür!

Wenn du es dir bis zu deinem Vertragsende doch anders überlegst, kannst du deinen Vertrag über den Mitgliederbereich einfach verlängern.

Aber auch wenn du keinen Ernteanteil mehr beziehst, freuen wir uns natürlich, dich bald mal wieder im WirGarten oder anderswo zu treffen!

Viele Grüße!
{admin_name} für das WirGarten-Team

P.S.: Es würde uns sehr helfen, wenn du uns Feedback gibt, warum du nicht verlängerst - antworte dazu einfach auf diese e-Mail.""",
            description="Inhalt der Email (HTML), die bei expliziter nicht-Verlängerung sofort an das Mitglied verschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=9978,
            meta=ParameterMeta(
                vars_hint=[
                    "contract_end_date",
                    "contract_list",
                ]
                + DEFAULT_EMAIL_MEMBER_VARS
                + DEFAULT_EMAIL_VARS,
                validators=[
                    validate_html,
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=ParameterKeys.EMAIL_CONTRACT_END_REMINDER_SUBJECT,
            label="Betreff: Email 'Vertrags-/Lieferende'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Dein letzter Ernteanteil",
            description="Betreff der Email, die bei Vertragsende nach der letzten Lieferung an das Mitglied geschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=7999,
        )

        parameter_definition(
            key=ParameterKeys.EMAIL_CONTRACT_END_REMINDER_CONTENT,
            label="Inhalt: Email 'Vertrags-/Lieferende'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Liebe/r {member.first_name}

Du hast diese Woche deine letzte Abholung gehabt. 

Folgende Produktverträge sind nun abgelaufen:

{contract_list}

Wenn du bereits Mitglied unserer Genossenschaft bist, bleibt dein Zugang zum Mitgliederbereich bestehen und du kannst - wenn Ernteanteile verfügbar sind - jederzeit über den Mitgliederbereich einen neuen Ernteanteil abschließen.

Wenn dies die letzte Abholung in deinem Probemonat war und du auch deinen Beitritt zur Genossenschaft widerrufen hast, löschen wir den Zugang zum Mitgliederbereich in den nächsten Tagen. Dann kannst du über unsere Website lueneburg.wirgarten.com einen neuen Ernteertrag abschließen, wenn du es dir anders überlegst.

Egal ob letzte Lieferung nach dem Probemonat oder nach einer oder mehreren Saisons - wir danken dir für deine Unterstützung und dein Vertrauen und freuen uns, dich auch ohne Ernteanteil mal wieder im WirGarten zu treffen!

Wenn du noch eine Frage oder Rückmeldung hast, melde dich gerne bei uns!

Viele Grüße und alles Gute,
{admin_name} aus deinem {site_name}

P.S.: Erzähle gerne Freund:innen, Nachbar:innen, Kolleg:innen in Lüneburg vom WirGarten!""",
            description="Inhalt der Email (HTML), die bei Vertragsende nach der letzten Lieferung an das Mitglied geschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=7998,
            meta=ParameterMeta(
                vars_hint=DEFAULT_EMAIL_MEMBER_VARS
                + DEFAULT_EMAIL_VARS
                + ["contract_list"],
                validators=[
                    validate_html,
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=ParameterKeys.EMAIL_CONTRACT_ORDER_CONFIRMATION_SUBJECT,
            label="Betreff: Email 'Bestellbestätigung'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine Vertragsdaten + Informationen zum Mitgliederbereich",
            description="Betreff der Email, die bei Vertragsabschluss/-verlängerung sofort an das Mitglied geschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=6999,
        )

        parameter_definition(
            key=ParameterKeys.EMAIL_CONTRACT_ORDER_CONFIRMATION_CONTENT,
            label="Inhalt: Email 'Bestelllbestätigung'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Liebe/r {member.first_name},

nachfolgend findest du alle wichtigen Vertragsdetails nochmal im Überblick:

{contract_list}

Wenn du <strong>Neumitglied</strong> bist, erhältst du in Kürze außerdem eine automatische Mail aus tapir (das ist unsere Mitglieder- und Ernteverwaltungssoftware), in der du gebeten wirst, dein Konto in tapir zu verifizieren. Bitte klicke einfach auf den Link und setze dann dein Passwort. Danach wirst du direkt in den Mitgliederbereich weitergeleitet. Im Mitgliederbereich findest du eine Übersicht über alle deine Verträge und kannst deine Daten, aber z.B. auch deinen Abholort, jederzeit ändern. Außerdem schicken wir dir  eine Willkommensmail mit allen wichtigen Informationen für Neumitglieder.

Wenn du schon <strong>Mitglied im WirGarten Lüneburg bist</strong>, hast du bereits einen Zugang zum Mitgliederbereich. Wir melden uns dann kurz vor der ersten Abholung der neuen Vertragslaufzeit nochmal mit einer Infomail bei dir!

Solltest du Fragen oder Unklarheiten haben, kannst du dich bei Lukas melden:

<strong>{admin_name}</strong>
{admin_telephone}
{site_email}

<img src="{admin_image}"/>
""",
            description="Inhalt der Email (HTML), die bei Vertragsende nach der letzten Lieferung an das Mitglied geschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=6998,
            meta=ParameterMeta(
                vars_hint=[
                    "contract_list",
                    "contract_start_date",
                    "contract_end_date",
                    "first_pickup_date",
                ]
                + DEFAULT_EMAIL_MEMBER_VARS
                + DEFAULT_EMAIL_VARS,
                validators=[
                    validate_html,
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=ParameterKeys.MEMBER_BYPASS_KEYCLOAK,
            label="TEMPORÄR: Umgehe Keycloak bei der Erstellung von Accounts",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Wenn aktiv, dann werden User nur in Tapir angelegt, ohne den Keycloak Account. Solange das der Fall ist, können sich diese User nicht anmelden.",
            category=ParameterCategory.MEMBER_DASHBOARD,
            enabled=False,
        )

        parameter_definition(
            key=ParameterKeys.EMAIL_CONTRACT_CHANGE_CONFIRMATION_SUBJECT,
            label="Betreff: Email 'Vertragsänderung'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine Vertragsänderung",
            description="Betreff der Email, die bei Erntevertragsänderung sofort an das Mitglied geschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=6899,
        )

        parameter_definition(
            key=ParameterKeys.EMAIL_CONTRACT_CHANGE_CONFIRMATION_CONTENT,
            label="Inhalt: Email 'Vertragsänderung'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Liebe/r {member.first_name},

wir bestätigen dir hiermit deine Vertragsänderung. Diese wird zum nächsten Monatsersten wirksam. Bis dahin bleiben deine Vertragsdaten gleich.

Deine neuen Daten sind:

{contract_list}

Im Mitgliederbereich findest du eine Zahlungs-und Lieferübersicht, da kannst du nochmal genau sehen, wann und wie die Änderung in Kraft tritt.

Wenn du Fragen hast oder dir etwas unklar ist, meld dich bitte bei uns!

Dein WirGarten-Team""",
            description="Inhalt der Email (HTML), die bei Erntevertragsänderung sofort an das Mitglied geschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=6898,
            meta=ParameterMeta(
                vars_hint=[
                    "contract_list",
                    "contract_start_date",
                    "contract_end_date",
                    "first_pickup_date",
                ]
                + DEFAULT_EMAIL_MEMBER_VARS
                + DEFAULT_EMAIL_VARS,
                validators=[
                    validate_html,
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=ParameterKeys.JOKERS_ENABLED,
            label="Joker-Feature einschalten",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Temporäre Liefer-Pausen pro Mitglied erlauben",
            category=ParameterCategory.JOKERS,
            order_priority=3,
        )

        parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL,
            label="Automatische Verlängerung der Verträge",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=3,
            enabled=is_debug_instance(),
        )

        parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD,
            label="Kündigungsfrist",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Bei automatischer Verlängerung der Verträge",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=2,
            enabled=is_debug_instance(),
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
                )
            ),
        )

        parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT,
            label="Einheit der Kündigungsfrist",
            datatype=TapirParameterDatatype.STRING,
            initial_value=NOTICE_PERIOD_UNIT_MONTHS,
            description="Ob der Feld Kündigungsfrist Monate oder Wochen angibt",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=1,
            meta=ParameterMeta(options=NOTICE_PERIOD_UNIT_OPTIONS),
            enabled=is_debug_instance(),
        )

        parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT,
            label="Einheit der Kündigungsfrist",
            datatype=TapirParameterDatatype.STRING,
            initial_value=NOTICE_PERIOD_UNIT_MONTHS,
            description="Ob der Feld Kündigungsfrist Monate oder Wochen angibt",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=1,
            meta=ParameterMeta(options=NOTICE_PERIOD_UNIT_OPTIONS),
            enabled=is_debug_instance(),
        )

        parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            label="Zusatzproduktverträge erlauben ohne Basisproduktvertrag",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Wenn dieses Feld aus ist, können Zusatzproduktverträge nur gezeichnet werden "
            "wenn das Mitglied mindestens ein Basisproduktvertrag gezeichnet hat.",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=0,
        )

        parameter_definition(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS,
            label="Rechtsform der Organisation",
            datatype=TapirParameterDatatype.STRING,
            initial_value=LEGAL_STATUS_COOPERATIVE,
            description="",
            category=ParameterCategory.ORGANIZATION,
            order_priority=10,
            meta=ParameterMeta(options=LEGAL_STATUS_OPTIONS),
            enabled=is_debug_instance(),
        )

        parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_WAITING_LIST_CATEGORIES,
            label="Warteliste-Kategorien",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Kategorie 1, Kategorie 2, Kategorie 3",
            description="Kategorien die in an Einträge der Warteliste zugewiesen werden können. Format: Kategorien-Namen mit ',' separiert. Anzahl beliebig",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=1,
        )

        if getattr(settings, "DEBUG", False):
            parameter_definition(
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

            parameter_definition(
                key=ParameterKeys.TESTS_OVERRIDE_DATE,
                label="Beliebiges Test-Datum",
                datatype=TapirParameterDatatype.STRING,
                initial_value="2025-04-01 09:30",
                description="Format: YYYY-MM-DD HH:MM.<br />"
                f'Wird nur eingesetzt wenn der Parameter "Datum festlegen" gleich Oben zu "Manuell" gesetzt ist.',
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
