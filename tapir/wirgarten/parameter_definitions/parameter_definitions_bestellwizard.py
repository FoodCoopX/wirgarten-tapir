import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.solidarity_contribution.config import (
    OPTIONS_BESTELL_WIZARD_SOLIDARITY_STEP_POSITION,
    BESTELL_WIZARD_SOLIDARITY_STEP_POSITION_BEFORE_PERSONAL_DATA,
)
from tapir.wirgarten.constants import ParameterCategory, HTML_ALLOWED_TEXT
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsBestellwizard:
    @classmethod
    def define_all_member_bestellwizard(cls, importer: ParameterDefinitions):
        bestellwizard_parameter_order = 100
        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_FORCE_WAITING_LIST,
            label="BestellWizard in Warteliste-Modus",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Wenn aktiviert, bestehende und neue Mitglieder können keine neue Produkt-Anteile buchen, egal ob es Kapazitäten gibt."
            "Wenn ausgeschaltet, Produkt-Anteile können gebucht werden wenn es genug Kapazitäten gibt.",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_SHOW_INTRO,
            label="Intro-Seite zeigen",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Wenn aktiviert, erscheint eine Intro-Seite, auf der der Benutzer auswählen kann, welche Produktanteile gezeichnet werden sollen. "
            "Wenn nicht aktiviert, werden alle Formularseiten zu allen Produktanteilen angezeigt.",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_INTRO_TEXT,
            label="Text im BestellWizard in der Intro-Seite Oben",
            datatype=TapirParameterDatatype.STRING,
            initial_value="""<h3 class='card-title'>Dieser Standard-Text soll in der Allgemein-Konfig angepasst werden</h3>
<p>
    Du möchtest Teil des COOP_NAME werden? Dann gibt es jetzt verschiedene Möglichkeiten:
</p>
<p>
    Das COOP_NAME ist eine Genossenschaft. Es gehört allen Mitgliedern, und nur Mitglieder können weitere Verträge abschließen und damit Gemüse beziehen.
</p>
<p>
    Du bist bereits Mitglied? Dann schließe bitte weitere Verträge über deinen persönlichen <a href={"/"}>Mitglieder-Bereich</a> ab.
</p>""",
            category=ParameterCategory.BESTELLWIZARD,
            description="Kann Text oder HTML sein",
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.BESTELLWIZARD_SHOW_INTRO, cache=cache
                ),
                textarea=True,
            ),
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELL_WIZARD_SOLIDARITY_STEP_POSITION,
            label="Position der Schritt 'Solidarbeitrag' in der Reihenfolge der Seiten",
            datatype=TapirParameterDatatype.STRING,
            initial_value=BESTELL_WIZARD_SOLIDARITY_STEP_POSITION_BEFORE_PERSONAL_DATA,
            category=ParameterCategory.BESTELLWIZARD,
            description="",
            meta=ParameterMeta(options=OPTIONS_BESTELL_WIZARD_SOLIDARITY_STEP_POSITION),
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_SEPA_MANDAT_CHECKBOX_TEXT,
            label="Text zum Checkbox zum SEPA-Mandat bei der Persönliche-Daten-Seite",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ich ermächtige den Betrieb die monatlichen Beträge für weitere Verträge mittels Lastschrift von meinem Bankkonto einzuziehen. Zugleich weise ich mein Kreditinstitut an, die gezogene Lastschrift einzulösen.",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(textarea=True),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_CONTRACT_POLICY_CHECKBOX_TEXT,
            label="Text zum Checkbox zu Vertragsgrundsätze",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ich habe die Vertragsgrundsätze/Gebührenordnung gelesen und akzeptiere diese.",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(textarea=True),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_BACKGROUND_COLOR,
            label="Hintergrundfarbe im BestellWizard",
            datatype=TapirParameterDatatype.STRING,
            initial_value="#ffffff",
            description="Typischerweise im Hexadecimal-Format, z.B. '#3AA551'",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_BACKGROUND_IMAGE,
            label="Hintergrundbild im BestellWizard",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="Als URL. Wenn nicht leer nimmt das Bild die Priorität über der Farbe.",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP1A_TITLE,
            label="Seite 1A: Begrüßungsseite - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schön, dass du Teil unserer Gemeinschaft werden willst!",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP1A_TEXT,
            label="Seite 1A: Begrüßungsseite - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Starte mit dem Bestellformular, damit du bald frisches Gemüse von uns erhältst.",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP1_BACKGROUND_IMAGE,
            label="Seite 1A & B: Begrüßungsseite - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="/static/lueneburg/registration/confirmation_1.jpg",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP1B_TITLE,
            label="Seite 1B: Begrüßungsseite im Wartelistemodus - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schön, dass du Teil unserer Gemeinschaft werden willst!",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP1B_TEXT,
            label="Seite 1B: Begrüßungsseite im Wartelistemodus - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Da wir derzeit keine freien Kapazitäten haben, kannst du dich nur auf die Warteliste setzen lassen. Wir kontaktieren dich dann, sobald ein passender Anteil freigeworden ist.",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP2_TITLE,
            label="Seite 2: Vorname - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Los geht’s: Wie heißt du?",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP2_TEXT,
            label="Seite 2: Vorname - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP2_BACKGROUND_IMAGE,
            label="Seite 2: Vorname - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="/static/lueneburg/registration/confirmation_2.jpg",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP3_TITLE,
            label="Seite 3: Produktauswahl - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{vorname}, an welchen Anteilen hast du Interesse?",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP3_TEXT,
            label="Seite 3: Produktauswahl - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP3_BACKGROUND_IMAGE,
            label="Seite 3: Produktauswahl - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="/static/lueneburg/registration/confirmation_3.jpg",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP3B_TITLE,
            label="Seite 3B: Vertragsperiode-Auswahl - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{vorname}, wann soll dein Vertrag starten?",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP3B_TEXT,
            label="Seite 3B: Vertragsperiode-Auswahl - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du kannst auswählen, ob dein Vertrag zur neuen oder bereits jetzt zur aktuellen Vertragsperiode starten soll. Es wird dir für beide Auswahloptionen jeweils das Startdatum deines Vertrages angezeigt (jeweils Mo. der ersten Lieferwoche).",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELL_WIZARD_STEP4B_WAITING_LIST_MODAL_HEADER,
            label="Seite 4B: Produkt-Typ Bestellung - Popup zu Warteliste - Title",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Warteliste",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELL_WIZARD_STEP4B_WAITING_LIST_MODAL_TEXT,
            label="Seite 4B: Produkt-Typ Bestellung - Popup zu Warteliste - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Diese standard Text zu Warteliste soll in der Konfig unter 'Seite 4B: Produkt-Typ Bestellung - Popup zu Warteliste - Text' angepasst werden",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP4D_TITLE,
            label="Seite 4D: Solidarbeitrag - Title",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Solidarbeitrag",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP4D_TEXT,
            label="Seite 4D: Solidarbeitrag - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Mit einer solidarischen Zahlung erlaubst du weniger finanzstarken Mitgliedern ebenfalls Mitgliedschaften in der Genossenschaft abzuschließen.",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP4D_BACKGROUND_IMAGE,
            label="Seite 4D: Solidarbeitrag - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP5A_TITLE,
            label="Seite 5A: Abholort Einführung - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Unsere Verteilstationen",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP5A_TEXT,
            label="Seite 5A: Abholort Einführung - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="<p>Auf der nächsten Seite kannst du dir eine Karte mit den Verteilstationen "
            "bzw. eine Liste dieser anzeigen lassen.</p><p>Du kannst deine Station während der "
            "Vertragslaufzeit im Mitgliederbereich auch wechseln z.B. wenn du umziehst.</p>",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(textarea=True),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP5_BACKGROUND_IMAGE,
            label="Seite 5 A&B: Abholort - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="/static/lueneburg/registration/pickup-location.jpg",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP5B_TITLE,
            label="Seite 5B: Abholort Auswahl - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="An welcher Verteilstation möchtest du abholen?",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP5C_TITLE,
            label="Seite 5C: Bestätigung der Verteilstation - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Verteilstation-Wünsche",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP5C_TEXT,
            label="Seite 5C: Bestätigung der Verteilstation - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine ausgewählte Verteilstation ist gerade ausgelastet und du kommst auf die Warteliste. Willst du noch weitere Stationen als Wunsch hinterlegen, damit du schneller einsteigen kannst?",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6A_TITLE,
            label="Seite 6A: Genossenschaft Einführung - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Unsere Genossenschaft",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6A_TEXT,
            label="Seite 6A: Genossenschaft Einführung - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="<p>Als Mitglied unserer Genossenschaft bist du gleichzeitig Miteigentümer*In deiner eigenen Gemüsegärtnerei! Du kannst somit bei allen Grundsatzentscheidungen mitbestimmen und hast ein Stimmrecht bei der Generalversammlung. </p><p>"
            "Mit deinen Genossenschaftsanteilen ermöglichst du die gemeinsame Finanzierung wichtiger Investitionen für die Genossenschaft.</p>",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(textarea=True),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6_BACKGROUND_IMAGE,
            label="Seite 6 A&B: Genossenschaftsanteile - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6B_TITLE,
            label="Seite 6B: Genossenschaftsanteile - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Wieviele Anteile willst du zeichnen, {vorname}?",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6B_TEXT,
            label="Seite 6B: Genossenschaftsanteile - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="<p>Standardtext zu Genoanteile. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam faucibus enim vel quam commodo porta.</p>",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(textarea=True),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_CHECKBOX_STATUTE,
            label="Seite 6B: Genossenschaft - Rechtliches - Checkbox-Label Satzung gelesen",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ich habe die <a href='{link_zu_satzung}' target='_blank'>Satzung</a> der {betriebsname} und die Kündigungsfrist von (2) Jahren zum Jahresende zur Kenntnis genommen.",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["betriebsname", "link_zu_satzung"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_TEXT_STATUTE,
            label="Seite 6B: Genossenschaft - Rechtliches - Erklärtext Satzung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Bitte beachte, dass deine Genossenschaftsanteile erst bei Austritt aus der Genossenschaft und nach Verabschiedung des Jahresabschlusses im Folgejahr zurückgezahlt werden dürfen. Siehe dazu Satzung § 10 und § 37.",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_CHECKBOX_COMMITMENT,
            label="Seite 6B: Genossenschaft - Rechtliches - Checkbox-Label Verpflichtung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ich verpflichte mich hiermit, die nach Gesetz und Satzung geschuldeten Einzahlungen auf die gezeichneten Geschäftsanteile zu leisten.",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_TITLE,
            label="Seite 6C: Sofort oder später Mitglied werden - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Möchtest du sofort Mitglied werden?",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP6C_TEXT,
            label="Seite 6C: Sofort oder später Mitglied werden - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Die wirst auf die Warteliste für deine Bestellung eingetragen. Du kannst dich aber entscheiden sofort Mitglied der Genossenschaft zu werden.",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP8_TITLE,
            label="Seite 8: Persönliche Daten - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Fast geschafft, {vorname}. Wir brauchen nur noch ein paar persönliche Daten von dir.",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP8_TEXT,
            label="Seite 8: Persönliche Daten - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine Daten brauchen wir aus gründe XYZ.",
            description=f"{HTML_ALLOWED_TEXT}. Optional.",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP8_BACKGROUND_IMAGE,
            label="Seite 8: Persönliche Daten - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP9_TITLE,
            label="Seite 9: Bankverbindung - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Für die Abwicklung der Zahlungen benötigen wir noch deine Bankverbindung.",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP9_BACKGROUND_IMAGE,
            label="Seite 9: Bankverbindung - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP9_PAYMENT_RHYTHM_MODAL_TEXT,
            label="Seite 9: Bankverbindung - Erklärungstext Zahlungsintervalle",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Dieses Text soll in der Konfig angepasst werden unter 'Seite 9: Bankverbindung - Erklärungstext Zahlungsintervalle'",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP10_TITLE,
            label="Seite 10: Zusammenfassung - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{vorname}, hier nochmal deine Bestellung auf einen Blick",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP10_BACKGROUND_IMAGE,
            label="Seite 10: Zusammenfassung - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP11_TITLE,
            label="Seite 11: Widerruf und Datenschutz - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du musst uns noch deine Zustimmung geben, damit wir dir bald frisches Gemüse liefern können",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP11_BACKGROUND_IMAGE,
            label="Seite 11: Widerruf und Datenschutz - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_PRIVACY_POLICY_LABEL,
            label="Seite 11: Label zu Checkbox zur Datenschutzerklärung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ja, ich habe die Datenschutzerklärung zur Kenntnis genommen.",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(textarea=True),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_PRIVACY_POLICY_EXPLANATION,
            label="Seite 11: Erklärungstext unter dem Checkbox zur Datenschutzerklärung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Wir behandeln deine Daten vertraulich, verwenden diese nur im Rahmen der Mitgliederverwaltung und geben sie nicht an Dritte weiter. "
            'Unsere Datenschutzerklärung kannst du hier einsehen: <a href="{{link_zu_datenschutzerklärung}}">Datenschutzerklärung</a>',
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(
                textarea=True, vars_hint=["link_zu_datenschutzerklärung"]
            ),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_REVOCATION_RIGHTS_LABEL,
            label="Seite 11: Label Checkbox zur Widerrufsbelehrung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ja, ich habe die Widerrufsbelehrung zur Kenntnis genommen.",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(textarea=True),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_REVOCATION_RIGHTS_EXPLANATION,
            label="Seite 11: Erklärungstext unter dem Checkbox zur Widerrufsbelehrung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du kannst deine Verträge innerhalb von zwei Wochen in Textform (z.B. Brief, E-Mail) widerrufen. Die Frist beginnt spätestens mit Erhalt dieser Belehrung. Zur Wahrung der Widerrufsfrist genügt die rechtzeitige Absendung eines formlosen Widerrufsschreibens an der Verwaltung.",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(textarea=True),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP12_TITLE,
            label="Seite 12: Vertriebskanal - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{vorname}, hast du noch einen Moment? Dann verrate uns, wie du eigentlich auf uns aufmerksam geworden bist?",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP12_BACKGROUND_IMAGE,
            label="Seite 12: Vertriebskanal - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP13_ENABLED,
            label="Seite 13: Feedback - aktiviert",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Ob die Feedback-Seite aktiviert ist oder nicht",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP13_TITLE,
            label="Seite 13: Feedback - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Hast du zum Abschluss noch ein Feedback für uns?",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(
                vars_hint=["vorname"],
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.BESTELLWIZARD_STEP13_ENABLED, cache=cache
                ),
            ),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP13_TEXT,
            label="Seite 13: Feedback - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Deine Anregungen helfen uns weiter, unser Angebot stetig zu verbessern",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.BESTELLWIZARD_STEP13_ENABLED, cache=cache
                ),
            ),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP13_BACKGROUND_IMAGE,
            label="Seite 13: Feedback - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.BESTELLWIZARD_STEP13_ENABLED, cache=cache
                ),
            ),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP14_TITLE,
            label="Seite 14: Abschluss - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Schön, dass du nun mit dabei bist {vorname}",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP14_TEXT,
            label="Seite 14: Abschluss - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du erhältst im Anschluss zwei Emails an <strong>{{mitglieder_mail}}</strong>. Schau bitte auch in dein SPAM-Posteingang. Sofern du innerhalb von 24 Stunden keine Mails erhalten hast, dann wende dich an unser Support unter {{kontakt_mail}}",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(
                vars_hint=["mitglieder_mail", "kontakt_mail"], textarea=True
            ),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP14_BACKGROUND_IMAGE,
            label="Seite 14: Abschluss - Hintergrundbild",
            datatype=TapirParameterDatatype.STRING,
            initial_value="/static/lueneburg/registration/confirmation.jpg",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP14B_TITLE,
            label="Seite 14B: Abschluss (Warteliste) - Titel",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du bist jetzt auf der Warteliste, {vorname}",
            description="",
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(vars_hint=["vorname"]),
        )
        bestellwizard_parameter_order -= 1

        importer.parameter_definition(
            key=ParameterKeys.BESTELLWIZARD_STEP14B_TEXT,
            label="Seite 14B: Abschluss (Warteliste) - Text",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du erhältst im Anschluss ein Email an <strong>{{mitglieder_mail}}</strong>. Schau bitte auch in dein SPAM-Posteingang. Sofern du innerhalb von 24 Stunden keine Mails erhalten hast, dann wende dich an unser Support unter {{kontakt_mail}}",
            description=HTML_ALLOWED_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            order_priority=bestellwizard_parameter_order,
            meta=ParameterMeta(
                vars_hint=["mitglieder_mail", "kontakt_mail"], textarea=True
            ),
        )
        bestellwizard_parameter_order -= 1
