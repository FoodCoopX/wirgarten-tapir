from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    EmailValidator,
    URLValidator,
)
from django.utils.translation import gettext_lazy as _
from localflavor.generic.validators import IBANValidator, BICValidator

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
    EMAIL = "Email"


class Parameter:
    SITE_NAME = f"{PREFIX}.site.name"
    SITE_STREET = f"{PREFIX}.site.street"
    SITE_CITY = f"{PREFIX}.site.city"
    SITE_EMAIL = f"{PREFIX}.site.email"
    SITE_ADMIN_EMAIL = f"{PREFIX}.site.admin_email"
    SITE_ADMIN_NAME = f"{PREFIX}.site.admin_name"
    SITE_ADMIN_TELEPHONE = f"{PREFIX}.site.admin_telephone"
    SITE_ADMIN_IMAGE = f"{PREFIX}.site.admin_image"
    SITE_PRIVACY_LINK = f"{PREFIX}.site.privacy_link"
    SITE_FAQ_LINK = f"{PREFIX}.site.faq_link"
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
    MEMBER_RENEWAL_ALERT_WAITLIST_HEADER = (
        f"{PREFIX}.member.dashboard.renewal_alert.waitlist.header"
    )
    MEMBER_RENEWAL_ALERT_WAITLIST_CONTENT = (
        f"{PREFIX}.member.dashboard.renewal_alert.waitlist.content"
    )
    EMAIL_CANCELLATION_CONFIRMATION_SUBJECT = (
        f"{PREFIX}.email.cancellation_confirmation.subject"
    )
    EMAIL_CANCELLATION_CONFIRMATION_CONTENT = (
        f"{PREFIX}.email.cancellation_confirmation.content"
    )
    EMAIL_NOT_RENEWED_CONFIRMATION_SUBJECT = (
        f"{PREFIX}.email.not_renewed_confirmation.subject"
    )
    EMAIL_NOT_RENEWED_CONFIRMATION_CONTENT = (
        f"{PREFIX}.email.not_renewed_confirmation.content"
    )
    EMAIL_CONTRACT_END_REMINDER_SUBJECT = (
        f"{PREFIX}.email.contract_end_reminder.subject"
    )
    EMAIL_CONTRACT_END_REMINDER_CONTENT = (
        f"{PREFIX}.email.contract_end_reminder.content"
    )
    EMAIL_CONTRACT_ORDER_CONFIRMATION_SUBJECT = (
        f"{PREFIX}.email.contract_order_confirmation.subject"
    )
    EMAIL_CONTRACT_ORDER_CONFIRMATION_CONTENT = (
        f"{PREFIX}.email.contract_order_confirmation.content"
    )


from tapir.configuration.models import (
    TapirParameterDatatype,
    TapirParameterDefinitionImporter,
)


class ParameterDefinitions(TapirParameterDefinitionImporter):
    def import_definitions(self):
        from tapir.configuration.parameter import parameter_definition, ParameterMeta
        from tapir.wirgarten.constants import ProductTypes
        from tapir.wirgarten.models import ProductType
        from tapir.wirgarten.validators import validate_format_string, validate_html

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
            key=Parameter.SITE_ADMIN_NAME,
            label="Admin/Ansprechpartner Name",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Lukas Heidelberg",
            description="Der Name des Ansprechpartners für Mitglieder",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.SITE_ADMIN_TELEPHONE,
            label="Admin/Ansprechpartner Telefonnummer",
            datatype=TapirParameterDatatype.STRING,
            initial_value="+49 176 34 45 81 48",
            description="Die Kontakttelefonnummer für Mitglieder",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.SITE_ADMIN_IMAGE,
            label="Admin/Ansprechpartner Foto",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/wp-content/uploads/sites/4/2023/03/lukas-heidelberg-higher-res.jpg",
            description="Ein Foto der Kontaktperson für Mitglieder",
            category=ParameterCategory.SITE,
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
            key=Parameter.SITE_FAQ_LINK,
            label="Link zum Mitglieder-FAQ",
            datatype=TapirParameterDatatype.STRING,
            initial_value="https://lueneburg.wirgarten.com/faq",
            description="Der Link zum FAQ für Mitglieder",
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
            order_priority=801,
            meta=ParameterMeta(
                validators=[
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS)
                ],
            ),
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_UNKOWN_CONTENT,
            label="Text: Hinweis zur Vertragsverlängerung -> Mitglied hat weder verlängert noch gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Als <strong>bestehendes Mitglied</strong> hast du <strong>Vorrang</strong> beim Zeichnen von Ernteanteilen und Zusatzabos. Ab sofort kannst du deine Verträge für die <strong>nächste Saison</strong> verlängern.<br/><small>Andernfalls enden deine Verträge automatisch am {contract_end_date}.</small>""",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, sofern das Mitglied seine Verträge weder verlängert noch explizit gekündigt hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=800,
            meta=ParameterMeta(
                validators=[
                    validate_html,
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS),
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_CANCELLED_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Mitglied hat explizit gekündigt",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schade, dass du gehst {member.first_name}!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge explizit zum Ende der Saison gekündigt hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=701,
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
            initial_value="""Du wolltest keine neuen Ernteanteile für den Zeitraum <strong>{next_period_start_date} - {next_period_end_date}</strong> zeichnen. Hast du es dir anders überlegt? Dann verlängere jetzt hier deinen Erntevertrag.""",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge explizit zum Ende der Saison gekündigt hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=700,
            meta=ParameterMeta(
                textarea=True,
                validators=[
                    validate_html,
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS),
                ],
            ),
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_RENEWED_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Mitglied hat Verträge verlängert",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schön, dass du dabei bleibst {member.first_name}!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, wenn das Mitglied seine Verträge für die nächste Saison verlängert hat (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=601,
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
            order_priority=600,
            meta=ParameterMeta(
                validators=[
                    lambda x: validate_format_string(
                        x, MEMBER_RENEWAL_ALERT_VARS + ["contract_list"]
                    ),
                    validate_html,
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_WAITLIST_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Keine Kapazität (Warteliste)",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Wir haben keine Ernteanteile mehr, {member.first_name}!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, wenn das Mitglied weder gekündigt noch verlängert hat, aber die Kapazität für Ernteanteile aufgebraucht ist (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=501,
            meta=ParameterMeta(
                validators=[
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS)
                ]
            ),
        )

        parameter_definition(
            key=Parameter.MEMBER_RENEWAL_ALERT_WAITLIST_CONTENT,
            label="Text: Hinweis zur Vertragsverlängerung -> Keine Kapazität (Warteliste)",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine Verträge enden am <strong>{contract_end_date}</strong>. Leider gibt es keine freien Ernteanteile mehr für die nächste Anbausaison. Wenn du möchtest, benachrichtigen wir dich sobald wir wieder freie Ernteanteile haben.",
            description="Inhalt der Hinweisbox (HTML). Dieser Hinweis wird angezeigt, wenn das Mitglied weder gekündigt noch verlängert hat, aber die Kapazität für Ernteanteile aufgebraucht ist (erscheint 2 Monate vor Beginn der nächsten Anbauperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=500,
            meta=ParameterMeta(
                validators=[
                    lambda x: validate_format_string(x, MEMBER_RENEWAL_ALERT_VARS),
                    validate_html,
                ],
                textarea=True,
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
                options=list(map(lambda x: (x.id, x.name), ProductType.objects.all()))
            ),
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
            key=Parameter.EMAIL_CANCELLATION_CONFIRMATION_SUBJECT,
            label="Betreff: Email 'Kündigungsbestätigung'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Kündigungsbestätigung",
            description="Betreff der Email, die bei Kündigung sofort an das Mitglied verschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=9999,
        )

        parameter_definition(
            key=Parameter.EMAIL_CANCELLATION_CONFIRMATION_CONTENT,
            label="Inhalt: Email 'Kündigungsbestätigung'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Moin {member.first_name}, 

wir finden es sehr schade, dass Du deinen Erntevertrag kündigen willst, was wir dir hiermit zum <strong>{contract_end_date}</strong> bestätigen.

Wir freuen uns, wenn du uns mehr über deine Kündigungsgründe erzählen würdest. Das hilft uns immer zu schauen, ob und was wir verbessern können.
Für uns wäre es zudem sehr hilfreich, wenn Du dich mal in deinem Freundes- und Bekanntenkreis umhört, ob jemand deinen Ernteanteil eventuell übernehmen will, damit die Genossenschaft ausreichend finanziert ist. 
Du kannst deinen Erntevertrag dann auch schon vor Ablauf des Vertrages auf diese Person übertragen. Melde dich gerne einfach. 

Viele Grüße von {admin_name} aus deinem {site_name}""",
            description="Inhalt der Email (HTML), die bei Kündigung sofort an das Mitglied verschickt wird. Variablen: {member.*}, {admin_name}, {site_name}, {contract_end_date}, {contract_list}.",
            category=ParameterCategory.EMAIL,
            order_priority=9998,
            meta=ParameterMeta(
                validators=[
                    validate_html,
                    lambda x: validate_format_string(
                        x,
                        [
                            "contract_end_date",
                            "contract_list",
                        ]
                        + DEFAULT_EMAIL_MEMBER_VARS
                        + DEFAULT_EMAIL_VARS,
                    ),
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=Parameter.EMAIL_NOT_RENEWED_CONFIRMATION_SUBJECT,
            label="Betreff: Email 'Bestätigung: Explizit nicht verlängert'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schade, dass du gehst!",
            description="Betreff der Email, die bei expliziter nicht-Verlängerung sofort an das Mitglied verschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=9979,
        )

        parameter_definition(
            key=Parameter.EMAIL_NOT_RENEWED_CONFIRMATION_CONTENT,
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
            description="Inhalt der Email (HTML), die bei expliziter nicht-Verlängerung sofort an das Mitglied verschickt wird.. Variablen: {member.*}, {admin_name}, {site_name}, {contract_end_date}, {contract_list}.",
            category=ParameterCategory.EMAIL,
            order_priority=9978,
            meta=ParameterMeta(
                validators=[
                    validate_html,
                    lambda x: validate_format_string(
                        x,
                        [
                            "contract_end_date",
                            "contract_list",
                        ]
                        + DEFAULT_EMAIL_MEMBER_VARS
                        + DEFAULT_EMAIL_VARS,
                    ),
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=Parameter.EMAIL_CONTRACT_END_REMINDER_SUBJECT,
            label="Betreff: Email 'Vertrags-/Lieferende'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Dein letzter Ernteanteil",
            description="Betreff der Email, die bei Vertragsende nach der letzten Lieferung an das Mitglied geschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=7999,
        )

        parameter_definition(
            key=Parameter.EMAIL_CONTRACT_END_REMINDER_CONTENT,
            label="Inhalt: Email 'Vertrags-/Lieferende'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""Moin {member.first_name},

du hast deinen Erntevertrag beim {site_name} gekündigt und hast diese Woche deinen letzten Ernteanteil abgeholt. 
Wir finden es toll, dass du diese ersten, aufregenden Gemüse-Jahre mit uns gemeinsam bestritten und gestaltet hast und wir dich mit WirGarten-Gemüse versorgen konnten. 
Vielen Dank für dein Vertrauen und deine Unterstützung, denn ohne dich wäre dies alles nicht möglich gewesen!

Umso mehr bedauern wir es, dass du gehst! Wir würden uns sehr freuen, wenn du eines Tages doch wieder Lust hast, mit uns die Agrarwende im Kleinen weiter zu gestalten und du wieder regionales Gemüse aus dem WirGarten genießen willst. 
Und toll fänden wir es auch, wenn du uns deinen Freund*innen und Bekannten weiterempfiehlst! 
Aber auch ohne Ernteanteil freuen wir uns natürlich, dich bald mal wieder im WirGarten oder anderswo zu treffen. 

Viele Grüße und alles Gute,
{admin_name} aus deinem {site_name}""",
            description="Inhalt der Email (HTML), die bei Vertragsende nach der letzten Lieferung an das Mitglied geschickt wird. Variablen: {member.*}, {admin_name}, {site_name}",
            category=ParameterCategory.EMAIL,
            order_priority=7998,
            meta=ParameterMeta(
                validators=[
                    validate_html,
                    lambda x: validate_format_string(
                        x, DEFAULT_EMAIL_MEMBER_VARS + DEFAULT_EMAIL_VARS
                    ),
                ],
                textarea=True,
            ),
        )

        parameter_definition(
            key=Parameter.EMAIL_CONTRACT_ORDER_CONFIRMATION_SUBJECT,
            label="Betreff: Email 'Bestellbestätigung'",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine Vertragsdaten + Informationen zum Mitgliederbereich",
            description="Betreff der Email, die bei Vertragsabschluss/-verlängerung sofort an das Mitglied geschickt wird.",
            category=ParameterCategory.EMAIL,
            order_priority=6999,
        )

        parameter_definition(
            key=Parameter.EMAIL_CONTRACT_ORDER_CONFIRMATION_CONTENT,
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
            description="Inhalt der Email (HTML), die bei Vertragsende nach der letzten Lieferung an das Mitglied geschickt wird. Variablen: {member.*}, {admin_name}, {site_name}, {contract_list}, {first_pickup_date}, {contract_start_date}, {contract_end_date}",
            category=ParameterCategory.EMAIL,
            order_priority=6998,
            meta=ParameterMeta(
                validators=[
                    validate_html,
                    lambda x: validate_format_string(
                        x,
                        [
                            "contract_list",
                            "contract_start_date",
                            "contract_end_date",
                            "first_pickup_date",
                        ]
                        + DEFAULT_EMAIL_MEMBER_VARS
                        + DEFAULT_EMAIL_VARS,
                    ),
                ],
                textarea=True,
            ),
        )
