from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.db import models
from django.db.models import ExpressionWrapper, F
from django.db.models.functions import TruncMonth
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from tapir_mail.models import StaticSegment, StaticSegmentRecipient
from tapir_mail.service.segment import (
    register_base_segment,
    register_filter,
    register_segment,
)
from tapir_mail.service.token import register_tokens
from tapir_mail.service.triggers import register_trigger
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Member, PickupLocation, WaitingListEntry
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_next_growing_period,
)
from tapir.wirgarten.triggers.onboarding_trigger import OnboardingTrigger
from tapir.wirgarten.utils import get_today


# Absenden Bestellwizzard Mitgliedschaft + Ernteanteile
class Events:
    REGISTER_MEMBERSHIP_AND_SUBSCRIPTION = "register_membership_and_subscription"

    # Absenden Bestellwizzard Mitgliedschaft (nur Geno-Anteile)
    REGISTER_MEMBERSHIP_ONLY = "register_membership_only"

    # Vertragsänderungen im Mitgliederbereich (Erntevertrag erhöhen, dazubestellen, abbestellen, kündigen, nicht verlängern, verlängern, Abholort ändern)
    MEMBERAREA_CHANGE_CONTRACT = "memberarea_change_contract"

    # Mitgliedsdatenänderungen (e-Mail-Adresse, Bankdaten, Adresse)
    MEMBERAREA_CHANGE_DATA = "memberarea_change_data"

    # Mitglied kündigt im Probemonat
    TRIAL_CANCELLATION = "trial_cancellation"

    # Mitglied hat Vertrag explizit nicht verlängert
    CONTRACT_NOT_RENEWED = "contract_not_renewed"

    # Mitglied tritt der Genossenschaft bei (nach Ablauf der Probezeit)
    MEMBERSHIP_ENTRY = "membership_entry"

    # Letzte Abholung (es gibt keine weiteren Verträge mehr)
    FINAL_PICKUP = "final_pickup"

    # Mitglied hat Abholort geändert
    MEMBERAREA_CHANGE_PICKUP_LOCATION = "memberarea_change_pickup_location"

    # Mitglied möchte Email Adresse ändern, muss Bestätigungslink klicken
    MEMBERAREA_CHANGE_EMAIL_INITIATE = "memberarea_change_email_initiate"

    # Mitglied möchte Email Adresse ändern, hinweis wird an der neue Adresse geschickt das er die alte Adresse lesen soll
    MEMBERAREA_CHANGE_EMAIL_HINT = "memberarea_change_email_hint"

    # Email Adresse wurde erfolgreich geändert
    MEMBERAREA_CHANGE_EMAIL_SUCCESS = "memberarea_change_email_success"

    CONTRACT_CANCELLED = "contract_canceled"

    FILE_EXPORTED = "file_exported"


class Segments:
    COOP_MEMBERS = "Geno-Mitglieder"
    NON_COOP_MEMBERS = "Nicht Geno-Mitglieder"
    WITH_ACTIVE_SUBSCRIPTION = "Mit laufendem Ertevertrag"
    WITHOUT_ACTIVE_SUBSCRIPTION = "Ohne laufenden Ertevertrag"


class Filters:
    CONTRACT_EXTENDED_YES = "Vertrag verlängert: ja"
    CONTRACT_EXTENDED_NO = "Vertrag verlängert: nein"
    CONTRACT_EXTENDED_NO_REACTION = "Vertrag verlängert: keine Reaktion"


def configure_mail_module():
    _register_segments()
    _register_filters()
    _register_tokens()
    _register_triggers()

    synchronize_waitlist_segments()


def _register_segments():
    base = Member.objects.all()
    register_base_segment(base)

    register_segment(
        Segments.COOP_MEMBERS,
        lambda: Member.objects.with_shares(),
    )

    register_segment(
        Segments.NON_COOP_MEMBERS,
        lambda: Member.objects.without_shares(),
    )

    register_segment(
        Segments.WITH_ACTIVE_SUBSCRIPTION,
        lambda: Member.objects.with_active_subscription(),
    )

    register_segment(
        Segments.WITHOUT_ACTIVE_SUBSCRIPTION,
        lambda: Member.objects.without_active_subscription(),
    )


def _register_filters():
    def create_contract_status_filter(expression):
        def filter_func(qs):
            next_growing_period = get_next_growing_period()

            if next_growing_period is None:
                return qs.none() if expression != "no reaction" else qs.all()

            if expression == "yes":
                return qs.filter(
                    subscription__start_date__gte=next_growing_period.start_date,
                    subscription__start_date__lte=next_growing_period.end_date,
                )

            elif expression == "no":
                trial_period_end_expr = ExpressionWrapper(
                    TruncMonth(F("subscription__start_date"))
                    + timedelta(
                        days=relativedelta(months=1).days,
                        seconds=relativedelta(months=1).seconds,
                    ),
                    output_field=models.DateField(),
                )

                return qs.annotate(trial_period_end=trial_period_end_expr).filter(
                    subscription__cancellation_ts__gt=F("trial_period_end"),
                    subscription__cancellation_ts__isnull=False,
                )

            elif expression == "no reaction":
                trial_period_start = get_today() + relativedelta(months=-1, day=1)

                return (
                    qs.filter(subscription__start_date__lte=trial_period_start)
                    .exclude(subscription__cancellation_ts__isnull=False)
                    .exclude(
                        subscription__start_date__gte=next_growing_period.start_date,
                        subscription__start_date__lte=next_growing_period.end_date,
                    )
                )

        return filter_func

    register_filter(Filters.CONTRACT_EXTENDED_YES, create_contract_status_filter("yes"))
    register_filter(Filters.CONTRACT_EXTENDED_NO, create_contract_status_filter("no"))
    register_filter(
        Filters.CONTRACT_EXTENDED_NO_REACTION,
        create_contract_status_filter("no reaction"),
    )

    for pl in PickupLocation.objects.all():
        register_filter(
            f"Abholort: {pl.name}",
            lambda qs, pl=pl: qs.filter(memberpickuplocation__pickup_location=pl),
        )


def _register_tokens():
    cache = {}
    register_tokens(
        user_tokens={
            "Vorname": "first_name",
            "Nachname": "last_name",
            "Email": "email",
            "Abholort": "pickup_location",
            "Mitglieds-Nr": "member_no",
            "Kontoempfänger": "account_owner",
            "IBAN": "iban",
            "Beitrittsdatum": "coop_entry_date",
            "Ernteanteilsgrößen": "base_subscriptions_text",
        },
        general_tokens={
            "WirGarten Standort": lambda: get_parameter_value(
                ParameterKeys.SITE_NAME, cache=cache
            ),
            "Admin Name": lambda: get_parameter_value(
                ParameterKeys.SITE_ADMIN_NAME, cache=cache
            ),
            "Admin Email": lambda: get_parameter_value(
                ParameterKeys.SITE_ADMIN_EMAIL, cache=cache
            ),
            "Admin Telefonnr": lambda: get_parameter_value(
                ParameterKeys.SITE_ADMIN_TELEPHONE, cache=cache
            ),
            "Admin Image": lambda: get_parameter_value(
                ParameterKeys.SITE_ADMIN_IMAGE, cache=cache
            ),
            "Kontakt Email": lambda: get_parameter_value(
                ParameterKeys.SITE_EMAIL, cache=cache
            ),
            "Datenschutzerklärung Link": lambda: get_parameter_value(
                ParameterKeys.SITE_PRIVACY_LINK, cache=cache
            ),
            "Mitglieder-FAQ Link": lambda: get_parameter_value(
                ParameterKeys.SITE_FAQ_LINK, cache=cache
            ),
            "Satzung Link": lambda: get_parameter_value(
                ParameterKeys.COOP_STATUTE_LINK, cache=cache
            ),
            "Infos zur Genossenschaft": lambda: get_parameter_value(
                ParameterKeys.COOP_INFO_LINK, cache=cache
            ),
            "Jahr (aktuell)": lambda: get_today(cache=cache).year,
            "Jahr (nächstes)": lambda: get_today(cache=cache).year + 1,
            "Jahr (übernächstes)": lambda: get_today(cache=cache).year + 2,
        },
    )
    pass


def _register_triggers():
    TransactionalTrigger.register_action(
        "BestellWizard: Mitgliedschaft + Ernteanteile",
        Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION,
        {
            "Vertragsliste": "contract_list",
            "Vertragsstart": "contract_start_date",
            "Vertragsende": "contract_end_date",
            "Erste Abholung am": "first_pickup_date",
        },
    )
    TransactionalTrigger.register_action(
        "BestellWizard: Nur Geno-Mitgliedschaft", Events.REGISTER_MEMBERSHIP_ONLY
    )
    TransactionalTrigger.register_action(
        "Vertragsänderungen im Mitgliederbereich",
        Events.MEMBERAREA_CHANGE_CONTRACT,
        {
            "Vertragsliste": "contract_list",
            "Vertragsstart": "contract_start_date",
            "Vertragsende": "contract_end_date",
            "Erste Abholung am": "first_pickup_date",
        },
    )
    TransactionalTrigger.register_action(
        "Mitgliedsdatenänderungen", Events.MEMBERAREA_CHANGE_DATA
    )
    TransactionalTrigger.register_action(
        "Abholortänderung",
        Events.MEMBERAREA_CHANGE_PICKUP_LOCATION,
        {
            "Neuer Abholort": "pickup_location",
            "Gültig ab": "pickup_location_start_date",
        },
    )

    TransactionalTrigger.register_action(
        name="Email-Änderung: Bestätigung anfordern",
        key=Events.MEMBERAREA_CHANGE_EMAIL_INITIATE,
        tokens={"Bestätigungslink": "verify_link"},
        required=True,
        default_content=get_default_mail_content(
            Events.MEMBERAREA_CHANGE_EMAIL_INITIATE
        ),
    )

    TransactionalTrigger.register_action(
        "Email-Änderung: Hinweis an neue Email die alte Adresse zu lesen",
        Events.MEMBERAREA_CHANGE_EMAIL_HINT,
    )

    TransactionalTrigger.register_action(
        name="Email-Änderung: Erfolg",
        key=Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS,
        required=True,
        default_content=get_default_mail_content(
            Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS
        ),
    )

    TransactionalTrigger.register_action(
        "Kündigung im Probemonat",
        Events.TRIAL_CANCELLATION,
        {
            "Vertragsliste": "contract_list",
            "Vertragsende": "contract_end_date",
            "Letzte Abholung am": "last_pickup_date",
        },
    )
    TransactionalTrigger.register_action(
        "Vertrag nicht verlängert", Events.CONTRACT_NOT_RENEWED
    )
    TransactionalTrigger.register_action(
        "Vertrag gekündigt",
        Events.CONTRACT_CANCELLED,
        {
            "Vertragsliste": "contract_list",
            "Vertragsende": "contract_end_date",
        },
    )
    TransactionalTrigger.register_action(
        "Beitritt zur Genossenschaft", Events.MEMBERSHIP_ENTRY
    )
    TransactionalTrigger.register_action(
        "Vertrags-/Lieferende",
        Events.FINAL_PICKUP,
        {"Vertragsliste": "contract_list"},
    )
    TransactionalTrigger.register_action(
        "Datei exportiert",
        Events.FILE_EXPORTED,
        {"Datei-Name": "file_name"},
    )

    register_trigger(OnboardingTrigger)


def get_default_mail_content(key: str) -> str:
    with open(f"tapir/wirgarten/email_drafts/{key}.mjml", "r") as file:
        return file.read()


def synchronize_waitlist_segment_for_entry(entry):
    static_segment, _ = StaticSegment.objects.get_or_create(name="Warteliste")

    recipient, created = StaticSegmentRecipient.objects.get_or_create(
        segment=static_segment,
        email=entry.email,
        defaults={"first_name": entry.first_name, "last_name": entry.last_name},
    )

    if not created:
        recipient.first_name = entry.first_name
        recipient.last_name = entry.last_name
        recipient.save()


def synchronize_waitlist_segments():
    for entry in WaitingListEntry.objects.all():
        synchronize_waitlist_segment_for_entry(entry)

    # Handle deletion of recipients no longer in WaitingList
    segment_name = "Warteliste"
    for recipient in StaticSegmentRecipient.objects.filter(segment__name=segment_name):
        if not WaitingListEntry.objects.filter(email=recipient.email).exists():
            print(f"Deleting recipient {recipient.email} from segment {segment_name}")
            recipient.delete()


@receiver(post_save, sender=WaitingListEntry)
def create_or_update_recipient(sender, instance, created, **kwargs):
    synchronize_waitlist_segment_for_entry(instance)


@receiver(post_delete, sender=WaitingListEntry)
def delete_recipient(sender, instance, **kwargs):
    try:
        static_segment = StaticSegment.objects.get(name="Warteliste")
        recipient = StaticSegmentRecipient.objects.get(
            segment=static_segment, email=instance.email
        )
        recipient.delete()
    except (StaticSegment.DoesNotExist, StaticSegmentRecipient.DoesNotExist):
        pass
