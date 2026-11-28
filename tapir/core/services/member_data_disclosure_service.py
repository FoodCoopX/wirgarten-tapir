import datetime
from collections.abc import Callable
from dataclasses import dataclass, field

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Count, Max, Min, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.text import capfirst

from tapir.accounts.models import EmailChangeRequest
from tapir.bakery.models import PreferredBread
from tapir.deliveries.models import DeliveryDonation, Joker
from tapir.associations.models import (
    AssociationDepositTransaction,
    AssociationMembership,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.log.models import EmailLogEntry, LogEntry
from tapir.payments.models import MemberCredit, MemberPaymentRhythm
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import (
    format_date,
    legal_status_is_association,
    legal_status_is_cooperative,
)
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
    # None: always shown; otherwise only when the feature is used by this organisation
    is_enabled: Callable[[dict], bool] | None = None


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
        exclude=frozenset({"secret"}),
        is_enabled=lambda cache: get_parameter_value(
            ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
        ),
    ),
    DataSource(
        key="email_change_requests",
        title="Offene Änderung der E-Mail-Adresse",
        purpose="Bestätigung einer neuen E-Mail-Adresse.",
        retention="Bis zur Bestätigung, längstens bis der Bestätigungslink abläuft.",
        model=EmailChangeRequest,
        member_lookup="user",
        exclude=frozenset({"user", "secret"}),
    ),
    DataSource(
        key="coop_shares",
        title="Genossenschaftsanteile",
        purpose="Mitgliederliste der Genossenschaft und Buchung der Anteile.",
        retention=RETENTION_BOOKKEEPING,
        model=CoopShareTransaction,
        member_lookup="member",
        # the transfer partner is another member
        exclude=frozenset({"transfer_member"}),
        is_enabled=legal_status_is_cooperative,
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
        is_enabled=legal_status_is_association,
    ),
    DataSource(
        key="association_deposit_transactions",
        title="Vereinseinlagen",
        purpose="Verwaltung der Vereinseinlage und ihrer Zahlungen.",
        retention=RETENTION_BOOKKEEPING,
        model=AssociationDepositTransaction,
        member_lookup="member",
        exclude=frozenset({"member"}),
        is_enabled=legal_status_is_association,
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
        exclude=frozenset(
            {
                "mandate_ref",
                "transaction",
                "coop_share_transaction",
                "association_deposit_transaction",
            }
        ),
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
        is_enabled=lambda cache: get_parameter_value(
            ParameterKeys.JOKERS_ENABLED, cache=cache
        ),
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
        key="preferred_breads",
        title="Brotwünsche",
        purpose="Planung der Backmengen und Verteilung der Brote.",
        retention=RETENTION_UNTIL_LEAVING,
        model=PreferredBread,
        member_lookup="member",
        fields=("breads",),
        is_enabled=lambda cache: settings.BAKERY_ENABLED,
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
        fields=("sources", "timestamp"),
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
    def build(cls, member: Member, cache: dict) -> dict:
        return {
            "generated_at": timezone.now(),
            "member": {
                "id": member.id,
                "member_no": member.member_no,
                "name": member.get_display_name(),
            },
            "sections": [
                cls._build_section(source, member)
                for source in DATA_SOURCES
                if source.is_enabled is None or source.is_enabled(cache)
            ],
            "log_overview": cls._build_log_overview(member),
            "mail_overview": cls._build_mail_overview(member),
            "pdf_url": reverse("core:member_data_disclosure_pdf")
            + "?"
            + urlencode({"member_id": member.id}),
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
        return capfirst(model_field.verbose_name)

    @staticmethod
    def _get_value(record: models.Model, model_field: models.Field) -> str | None:
        if model_field.many_to_many:
            names = [
                str(related) for related in getattr(record, model_field.name).all()
            ]
            return ", ".join(names) or None
        value = getattr(record, model_field.name)
        if value is None or value == "":
            return None
        if model_field.choices:
            return str(getattr(record, f"get_{model_field.name}_display")())
        if isinstance(value, bool):
            return "Ja" if value else "Nein"
        if isinstance(value, datetime.date):
            return format_date(value)
        return str(value)

    @staticmethod
    def _build_log_overview(member: Member) -> list[dict]:
        """Counts of log entries about the member by type, without the single entries."""
        rows = (
            LogEntry.objects.filter(
                Q(user=member)
                | Q(actor=member)
                | Q(transfercoopshareslogentry__target_member=member)
            )
            .values("log_class_type")
            .annotate(
                count=Count("id", distinct=True),
                first=Min("created_date"),
                last=Max("created_date"),
            )
        )
        overview = [
            {
                "type": capfirst(
                    ContentType.objects.get_for_id(row["log_class_type"]).name
                ),
                "count": row["count"],
                "first": row["first"],
                "last": row["last"],
            }
            for row in rows
        ]
        return sorted(overview, key=lambda entry: entry["type"])

    @staticmethod
    def _build_mail_overview(member: Member) -> dict:
        """Sent mails are stored as log entries. Only count and period are shown."""
        aggregate = EmailLogEntry.objects.filter(user=member).aggregate(
            count=Count("id"), first=Min("created_date"), last=Max("created_date")
        )
        return aggregate
