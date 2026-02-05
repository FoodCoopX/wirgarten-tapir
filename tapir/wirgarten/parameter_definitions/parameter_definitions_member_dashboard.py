import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.wirgarten.constants import ParameterCategory, OPTIONS_WEEKDAYS
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.validators import validate_html

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsMemberDashboard:
    @classmethod
    def define_all_parameters_member_dashboard(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL,
            label="Kommissioniervariable",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=6,
            description="Es gilt der gewählte Tag bis 23:59 Uhr. Tag, bis zu dem eine Abholort-Änderung möglich ist. Danach werden Kommissionier-Listen für die jeweilige Woche erstellt.",
            category=ParameterCategory.MEMBER_DASHBOARD,
            meta=ParameterMeta(options=OPTIONS_WEEKDAYS),
        )

        MEMBER_RENEWAL_ALERT_VARS = [
            "member",
            "contract_end_date",
            "next_period_start_date",
            "next_period_end_date",
        ]

        importer.parameter_definition(
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

        importer.parameter_definition(
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

        importer.parameter_definition(
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

        importer.parameter_definition(
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

        importer.parameter_definition(
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

        importer.parameter_definition(
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

        importer.parameter_definition(
            key=ParameterKeys.MEMBER_RENEWAL_ALERT_WAITLIST_HEADER,
            label="Überschrift: Hinweis zur Vertragsverlängerung -> Keine Kapazität (Warteliste)",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Wir haben keine Ernteanteile mehr, {member.first_name}!",
            description="Überschrift der Hinweisbox. Dieser Hinweis wird angezeigt, wenn das Mitglied weder gekündigt noch verlängert hat, aber die Kapazität für Ernteanteile aufgebraucht ist (erscheint 3 Monate vor Beginn der nächsten Vertragsperiode im Mitgliederbereich).",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=501,
            meta=ParameterMeta(vars_hint=MEMBER_RENEWAL_ALERT_VARS),
        )

        importer.parameter_definition(
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

        importer.parameter_definition(
            key=ParameterKeys.MEMBER_CANCELLATION_REASON_CHOICES,
            label="Kündigungsgründe",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Menge (zu viel); Menge (zu wenig); Preis; Vielfalt; Qualität; Weg-/Umzug",
            description="Die Kündigungsgründe, die ein Mitglied bei der Kündigung auswählen kann. Die einzelnen Gründe werden durch Semikolon ';' getrennt angegeben.",
            category=ParameterCategory.MEMBER_DASHBOARD,
            order_priority=400,
        )
