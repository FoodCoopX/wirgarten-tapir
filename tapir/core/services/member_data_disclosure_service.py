import datetime
from dataclasses import dataclass, field

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Count, Max, Min
from django.utils import timezone

from tapir.deliveries.models import DeliveryDonation, Joker
from tapir.associations.models import AssociationMembership
from tapir.log.models import EmailLogEntry, LogEntry
from tapir.payments.models import MemberCredit, MemberPaymentRhythm
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.models import (
    CoopShareTransaction,
    Deliveries,
    MandateReference,
    Member,
    MemberExtraEmail,
    MemberPickupLocation,
    OrderFeedback,
    Payment,
    QuestionaireCancellationReasonResponse,
    QuestionaireTrafficSourceResponse,
    Subscription,
    WaitingListEntry,
)

# Texts to Purpose and Retention are a technical proposal, see wiki "Betrieb-Datenschutz".
# Each cooperative has to confirm them with its auditing association or data protection officer.
RETENTION_UNTIL_LEAVING = (
    "Bis zum Ende der Mitgliedschaft, danach nur, soweit eine gesetzliche "
    "Aufbewahrungspflicht besteht."
)
RETENTION_BOOKKEEPING = (
    "Buchungsbelege unterliegen gesetzlichen Aufbewahrungsfristen "
    "(z. B. § 257 HGB, § 147 AO)."
)

NOT_DISCLOSED_FIELDS = {"id", "member"}


@dataclass(frozen=True)
class DataSource:
    key: str
    title: str
    purpose: str
    retention: str
    model: type[models.Model]
    member_lookup: str
    fields: tuple[str, ...] | None = None
    exclude: frozenset[str] = field(default_factory=frozenset)


DATA_SOURCES = [
    DataSource(
        key="personal_data",
        title="Stammdaten",
        purpose="Verwaltung der Mitgliedschaft und Kontakt zum Mitglied.",
        retention=RETENTION_UNTIL_LEAVING,
        model=Member,
        member_lookup="pk",
        fields=(
            "member_no",
            "form_of_address",
            "first_name",
            "last_name",
            "pseudonym",
            "birthdate",
            "email",
            "phone_number",
            "phone_number_landline",
            "street",
            "street_2",
            "postcode",
            "city",
            "country",
            "preferred_language",
            "is_student",
            "created_at",
            "privacy_consent",
        ),
    ),
    DataSource(
        key="banking_data",
        title="Bankdaten",
        purpose="Einzug der Beiträge per SEPA-Lastschrift.",
        retention=RETENTION_BOOKKEEPING,
        model=Member,
        member_lookup="pk",
        fields=("account_owner", "iban", "sepa_consent", "withdrawal_consent"),
    ),
    DataSource(
        key="mandates",
        title="SEPA-Mandate",
        purpose="Nachweis der Einzugsermächtigung.",
        retention=RETENTION_BOOKKEEPING,
        model=MandateReference,
        member_lookup="member",
    ),
    DataSource(
        key="extra_emails",
        title="Weitere E-Mail-Adressen",
        purpose="Zusätzliche Empfänger für Mitteilungen.",
        retention=RETENTION_UNTIL_LEAVING,
        model=MemberExtraEmail,
        member_lookup="member",
    ),
    DataSource(
        key="coop_shares",
        title="Genossenschaftsanteile",
        purpose="Mitgliederliste der Genossenschaft und Buchung der Anteile.",
        retention=RETENTION_BOOKKEEPING,
        model=CoopShareTransaction,
        member_lookup="member",
        # transfer partner and payment point to other people or to payment records
        exclude=frozenset({"transfer_member", "payment"}),
    ),
    DataSource(
        key="subscriptions",
        title="Verträge",
        purpose="Abwicklung der Ernteanteile und weiterer Produkte.",
        retention=RETENTION_BOOKKEEPING,
        model=Subscription,
        member_lookup="member",
    ),
    DataSource(
        key="association_memberships",
        title="Vereinsmitgliedschaft",
        purpose="Verwaltung der Mitgliedschaft im Verein.",
        retention=RETENTION_UNTIL_LEAVING,
        model=AssociationMembership,
        member_lookup="member",
    ),
    DataSource(
        key="solidarity_contributions",
        title="Solidarbeitrag",
        purpose="Abwicklung des Solidarbeitrags.",
        retention=RETENTION_BOOKKEEPING,
        model=SolidarityContribution,
        member_lookup="member",
    ),
    DataSource(
        key="payments",
        title="Zahlungen",
        purpose="Buchführung und Abrechnung der Beiträge.",
        retention=RETENTION_BOOKKEEPING,
        model=Payment,
        member_lookup="mandate_ref__member",
        exclude=frozenset({"mandate_ref", "transaction"}),
    ),
    DataSource(
        key="payment_rhythm",
        title="Zahlungsrhythmus",
        purpose="Festlegung, wie oft das Mitglied zahlt.",
        retention=RETENTION_UNTIL_LEAVING,
        model=MemberPaymentRhythm,
        member_lookup="member",
    ),
    DataSource(
        key="credits",
        title="Gutschriften",
        purpose="Buchführung und Abrechnung von Gutschriften.",
        retention=RETENTION_BOOKKEEPING,
        model=MemberCredit,
        member_lookup="member",
    ),
    DataSource(
        key="pickup_location",
        title="Abholort",
        purpose="Verteilung der Ernte.",
        retention=RETENTION_UNTIL_LEAVING,
        model=MemberPickupLocation,
        member_lookup="member",
    ),
    DataSource(
        key="deliveries",
        title="Lieferungen",
        purpose="Verteilung der Ernte.",
        retention=RETENTION_UNTIL_LEAVING,
        model=Deliveries,
        member_lookup="member",
    ),
    DataSource(
        key="jokers",
        title="Joker",
        purpose="Ausfall einer Lieferung und Abrechnung.",
        retention=RETENTION_UNTIL_LEAVING,
        model=Joker,
        member_lookup="member",
    ),
    DataSource(
        key="donations",
        title="Spenden von Lieferungen",
        purpose="Weitergabe nicht abgeholter Lieferungen.",
        retention=RETENTION_UNTIL_LEAVING,
        model=DeliveryDonation,
        member_lookup="member",
    ),
    DataSource(
        key="waiting_list",
        title="Warteliste",
        purpose="Verwaltung der Interessent*innen und Zuteilung von Plätzen.",
        retention="Bis die Anfrage erledigt ist oder zurückgezogen wird.",
        model=WaitingListEntry,
        member_lookup="member",
    ),
    DataSource(
        key="traffic_source",
        title="Wie bist du auf uns aufmerksam geworden?",
        purpose="Auswertung freiwilliger Angaben.",
        retention=RETENTION_UNTIL_LEAVING,
        model=QuestionaireTrafficSourceResponse,
        member_lookup="member",
    ),
    DataSource(
        key="cancellation_reasons",
        title="Kündigungsgründe",
        purpose="Auswertung freiwilliger Angaben.",
        retention=RETENTION_UNTIL_LEAVING,
        model=QuestionaireCancellationReasonResponse,
        member_lookup="member",
    ),
    DataSource(
        key="order_feedback",
        title="Rückmeldungen zur Bestellung",
        purpose="Verbesserung des Bestellvorgangs.",
        retention=RETENTION_UNTIL_LEAVING,
        model=OrderFeedback,
        member_lookup="member",
    ),
]


class MemberDataDisclosureService:
    """Collects the data stored about one member (Art. 15 and 20 GDPR)."""

    @classmethod
    def build(cls, member: Member) -> dict:
        return {
            "generated_at": timezone.now(),
            "member": {
                "id": member.id,
                "member_no": member.member_no,
                "name": f"{member.first_name} {member.last_name}".strip(),
            },
            "sections": [cls._build_section(source, member) for source in DATA_SOURCES],
            "log_overview": cls._build_log_overview(member),
            "mail_overview": cls._build_mail_overview(member),
        }

    @classmethod
    def _build_section(cls, source: DataSource, member: Member) -> dict:
        queryset = source.model.objects.filter(**{source.member_lookup: member})
        model_fields = cls._get_model_fields(source)
        return {
            "key": source.key,
            "title": source.title,
            "purpose": source.purpose,
            "retention": source.retention,
            "records": [
                [
                    {
                        "name": model_field.name,
                        "label": cls._get_label(model_field),
                        "value": cls._get_value(record, model_field),
                    }
                    for model_field in model_fields
                ]
                for record in queryset
            ],
        }

    @staticmethod
    def _get_model_fields(source: DataSource) -> list[models.Field]:
        if source.fields is not None:
            return [source.model._meta.get_field(name) for name in source.fields]
        return [
            model_field
            for model_field in source.model._meta.concrete_fields
            if model_field.name not in NOT_DISCLOSED_FIELDS
            and model_field.name not in source.exclude
        ]

    @staticmethod
    def _get_label(model_field: models.Field) -> str:
        label = str(model_field.verbose_name)
        return label[:1].upper() + label[1:]

    @staticmethod
    def _get_value(record: models.Model, model_field: models.Field) -> str | None:
        value = getattr(record, model_field.name)
        if value is None or value == "":
            return None
        if model_field.choices:
            return str(getattr(record, f"get_{model_field.name}_display")())
        if isinstance(value, bool):
            return "Ja" if value else "Nein"
        if isinstance(value, datetime.datetime):
            return timezone.localtime(value).strftime("%d.%m.%Y %H:%M")
        if isinstance(value, datetime.date):
            return value.strftime("%d.%m.%Y")
        if hasattr(value, "code") and hasattr(value, "name"):  # Country
            return str(value.name)
        return str(value)

    @staticmethod
    def _build_log_overview(member: Member) -> list[dict]:
        """Counts of log entries about the member by type, without the single entries."""
        rows = (
            LogEntry.objects.filter(user=member)
            .values("log_class_type")
            .annotate(
                count=Count("id"),
                first=Min("created_date"),
                last=Max("created_date"),
            )
        )
        content_types = ContentType.objects.in_bulk(
            [row["log_class_type"] for row in rows]
        )
        overview = []
        for row in rows:
            model_class = content_types[row["log_class_type"]].model_class()
            overview.append(
                {
                    "type": (
                        str(model_class._meta.verbose_name).capitalize()
                        if model_class
                        else content_types[row["log_class_type"]].model
                    ),
                    "count": row["count"],
                    "first": row["first"],
                    "last": row["last"],
                }
            )
        return sorted(overview, key=lambda entry: entry["type"])

    @staticmethod
    def _build_mail_overview(member: Member) -> dict:
        """Sent mails are stored as log entries. Only count and period are shown."""
        aggregate = EmailLogEntry.objects.filter(user=member).aggregate(
            count=Count("id"), first=Min("created_date"), last=Max("created_date")
        )
        return aggregate
