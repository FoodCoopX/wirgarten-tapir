from datetime import timedelta
from functools import partial
from typing import Callable

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
from tapir.core.services.newsletter_management_link_provider import (
    NewsletterManagementLinkProvider,
)
from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_mail_token_service import (
    PickupLocationMailTokenService,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.shortcuts import is_running_tests
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Member, PickupLocation, WaitingListEntry
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_next_growing_period,
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.triggers.onboarding_trigger import OnboardingTrigger
from tapir.wirgarten.utils import get_today, legal_status_is_cooperative

TOKENS_COOP_ENTRY = {
    "Anzahl der gezeichneten Genossenschaftsanteile": "number_of_coop_shares",
    "Wert Genossenschaftsanteil": "price_of_a_coop_share",
    "Gesamtwert der gezeichneten Genossenschaftsanteile": "total_cost",
    "Beitrittsdatum in der Genossenschaft": "membership_start_date",
}


class Segments:
    COOP_MEMBERS = "Geno-Mitglieder"
    NON_COOP_MEMBERS = "Nicht Geno-Mitglieder"
    WITH_ACTIVE_SUBSCRIPTION = "Mit laufendem Ertevertrag"
    WITHOUT_ACTIVE_SUBSCRIPTION = "Ohne laufenden Ertevertrag"
    MEMBERS_WITH_CONTRACT_SINCE_MORE_THAN_ONE_YEAR_BUT_NO = (
        "Mit Vertrag über einem Jahr aber kein Geno-Anteil"
    )


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

    register_segment(
        Segments.MEMBERS_WITH_CONTRACT_SINCE_MORE_THAN_ONE_YEAR_BUT_NO,
        lambda: MemberSegmentProvider.get_queryset_members_with_contract_since_more_than_one_year_but_no_coop_share(),
    )

    cache = {}
    for pickup_location in PickupLocation.objects.all():
        register_segment(
            "Abholort: " + pickup_location.name,
            partial(get_queryset_for_pickup_location, pickup_location, cache),
        )

    # Avoid checking the parameter during tests otherwise we need to import parameters in all the integration tests
    trial_period_enabled = not is_running_tests() and get_parameter_value(
        key=ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
    )
    if trial_period_enabled:
        register_segment(
            "Mitglieder im Probezeit", lambda: get_queryset_members_in_trial(cache)
        )


def get_queryset_for_pickup_location(pickup_location: PickupLocation, cache: dict):
    queryset = MemberPickupLocationGetter.annotate_member_queryset_with_pickup_location_id_at_date(
        queryset=Member.objects.all(), reference_date=get_today(cache)
    )

    return queryset.filter(
        **{
            MemberPickupLocationGetter.ANNOTATION_CURRENT_PICKUP_LOCATION_ID: pickup_location.id
        }
    )


def get_queryset_members_in_trial(cache: dict):
    today = get_today(cache)
    subscriptions_in_trial = [
        subscription
        for subscription in get_active_and_future_subscriptions(
            reference_date=today, cache=cache
        )
        if TrialPeriodManager.is_contract_in_trial(
            subscription, reference_date=today, cache=cache
        )
    ]
    member_ids_in_trial = {
        subscription.member_id for subscription in subscriptions_in_trial
    }
    return Member.objects.filter(id__in=member_ids_in_trial)


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
        dynamic_tokens={
            "Verteilstation - Name": PickupLocationMailTokenService.pickup_location_name,
            "Verteilstation - Adresse": PickupLocationMailTokenService.pickup_location_address,
            "Verteilstation - Zugangscode": PickupLocationMailTokenService.pickup_location_access_code,
            "Verteilstation - Signal-Gruppe": PickupLocationMailTokenService.pickup_location_messenger_group_link,
            "Verteilstation - Kontaktname": PickupLocationMailTokenService.pickup_location_contact_name,
            "Verteilstation - Photo-Link": PickupLocationMailTokenService.pickup_location_photo_link,
            "Verteilstation - Zusatzinfos": PickupLocationMailTokenService.pickup_location_info,
            "Verteilstation - Abholzeiten": PickupLocationMailTokenService.pickup_location_opening_times,
            "Newsletter - Verwaltungslink": NewsletterManagementLinkProvider.get_newsletter_management_link,
        },
    )


def _register_triggers():
    register_transactional_trigger(
        name="BestellWizard: Mitgliedschaft + Ernteanteile",
        key=Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION,
        tokens={
            "Vertragsliste": "contract_list",
            "Vertragsstart": "contract_start_date",
            "Vertragsende": "contract_end_date",
            "Erste Abholung am": "first_pickup_date",
        }
        | TOKENS_COOP_ENTRY,
        required=True,
    )
    TransactionalTrigger.register_action(
        "BestellWizard: Nur Geno-Mitgliedschaft",
        Events.REGISTER_MEMBERSHIP_ONLY,
        tokens=TOKENS_COOP_ENTRY,
    )
    register_transactional_trigger(
        name="Vertragsänderungen im Mitgliederbereich",
        key=Events.MEMBERAREA_CHANGE_CONTRACT,
        tokens={
            "Vertragsliste": "contract_list",
            "Vertragsstart": "contract_start_date",
            "Vertragsende": "contract_end_date",
            "Erste Abholung am": "first_pickup_date",
        },
        required=True,
    )
    TransactionalTrigger.register_action(
        "Mitgliedsdatenänderungen", Events.MEMBERAREA_CHANGE_DATA
    )
    register_transactional_trigger(
        name="Abholortänderung",
        key=Events.MEMBERAREA_CHANGE_PICKUP_LOCATION,
        tokens={
            "Neuer Abholort": "pickup_location",
            "Gültig ab": "pickup_location_start_date",
        },
        required=True,
    )

    register_transactional_trigger(
        name="Email-Änderung: Bestätigung anfordern",
        key=Events.MEMBERAREA_CHANGE_EMAIL_INITIATE,
        tokens={"Bestätigungslink": "verify_link"},
        required=True,
    )

    register_transactional_trigger(
        "Email-Änderung: Hinweis an neue Email die alte Adresse zu lesen",
        Events.MEMBERAREA_CHANGE_EMAIL_HINT,
        required=True,
    )

    register_transactional_trigger(
        name="Email-Änderung: Erfolg",
        key=Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS,
        required=True,
    )

    register_transactional_trigger(
        name="Kündigung im Probemonat",
        key=Events.TRIAL_CANCELLATION,
        tokens={
            "Vertragsliste": "contract_list",
            "Vertragsende": "contract_end_date",
            "Letzte Abholung am": "last_pickup_date",
        },
        required=lambda: get_parameter_value(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache={}
        ),
    )
    register_transactional_trigger(
        name="Vertrag nicht verlängert",
        key=Events.CONTRACT_NOT_RENEWED,
        required=lambda: not get_parameter_value(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache={}
        ),
    )
    register_transactional_trigger(
        name="Vertrag gekündigt",
        key=Events.CONTRACT_CANCELLED,
        tokens={
            "Vertragsliste": "contract_list",
            "Vertragsende": "contract_end_date",
        },
        required=True,
    )
    register_transactional_trigger(
        name="Beitritt zur Genossenschaft",
        key=Events.MEMBERSHIP_ENTRY,
        required=lambda: legal_status_is_cooperative(cache={}),
    )

    register_transactional_trigger(
        name="Vertrags-/Lieferende",
        key=Events.FINAL_PICKUP,
        tokens={"Vertragsliste": "contract_list"},
        required=True,
    )

    register_trigger(OnboardingTrigger)

    register_transactional_trigger(
        name="Bestätigung Eintrag Warteliste",
        key=Events.CONFIRMATION_REGISTRATION_IN_WAITING_LIST,
        tokens={
            "Vertragsliste": "contract_list",
            "Verteilstation Wünsche": "pickup_location_list",
            "Gewünschtes Startdatum": "desired_start_date",
        },
        required=True,
    )

    register_transactional_trigger(
        name="Warteliste Wunsch Link",
        key=Events.WAITING_LIST_WISH_CAN_BE_ORDERED,
        tokens={
            "Link zu Bestellwizard": "link",
        },
        required=True,
    )

    register_transactional_trigger(
        name="Bestellung durch Warteliste-Link abgeschlossen",
        key=Events.WAITING_LIST_ORDER_CONFIRMATION,
        tokens={
            "Vertragsliste": "contract_list",
            "Vertragsstart": "contract_start_date",
            "Vertragsende": "contract_end_date",
            "Erste Abholung am": "first_pickup_date",
        }
        | TOKENS_COOP_ENTRY,
        required=True,
    )

    register_transactional_trigger(
        name="Bestellung vom Admin bestätigt",
        key=Events.ORDER_CONFIRMED_BY_ADMIN,
        tokens={
            "Vertragsliste": "contract_list",
            "Anzahl an GenoAnteile": "number_of_coop_shares",
        },
        required=True,
    )

    register_transactional_trigger(
        name="Bestellung widerruft",
        key=Events.ORDER_REVOKED,
        tokens={
            "Vertragsliste": "contract_list",
            "Anzahl an GenoAnteile": "number_of_coop_shares",
        },
        required=True,
    )

    register_transactional_trigger(
        name="Extra Mail-Adresse muss bestätigt werden",
        key=Events.EXTRA_MAIL_CONFIRMATION,
        tokens={
            "Bestätigungslink": "confirmation_link",
            "Haupt-Mail-Adresse": "main_mail_address",
        },
        required=lambda: get_parameter_value(
            ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache={}
        ),
    )


def register_transactional_trigger(
    name: str, key: str, tokens: dict = None, required: bool | Callable = False
):
    TransactionalTrigger.register_action(
        name=name,
        key=key,
        required=required,
        tokens=tokens,
        default_content=get_default_mail_content(key=key) if required else None,
    )


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
        StaticSegmentRecipient.objects.filter(
            segment=static_segment, email=instance.email
        ).delete()
    except (StaticSegment.DoesNotExist, StaticSegmentRecipient.DoesNotExist):
        pass
