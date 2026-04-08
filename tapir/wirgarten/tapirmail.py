from typing import Callable

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from tapir_mail.models import StaticSegment, StaticSegmentRecipient
from tapir_mail.service.segment import register_base_segment
from tapir_mail.service.token import register_tokens
from tapir_mail.service.triggers import register_trigger
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.configuration.parameter import get_parameter_value
from tapir.core.services.newsletter_management_link_provider import (
    NewsletterManagementLinkProvider,
)
from tapir.pickup_locations.services.pickup_location_mail_token_service import (
    PickupLocationMailTokenService,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import WaitingListEntry, Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.triggers.onboarding_trigger import OnboardingTrigger
from tapir.wirgarten.utils import get_today, legal_status_is_cooperative

TOKENS_COOP_ENTRY = {
    "Anzahl der gezeichneten Genossenschaftsanteile": "number_of_coop_shares",
    "Wert Genossenschaftsanteil": "price_of_a_coop_share",
    "Gesamtwert der gezeichneten Genossenschaftsanteile": "total_cost",
    "Beitrittsdatum in der Genossenschaft": "membership_start_date",
}


class Segments:
    ALL_USERS = "Alle Benutzer"
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
    base = Member.objects.all()
    register_base_segment(base)

    _register_tokens()
    _register_triggers()


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
            "Verteilstation - Messenger-Gruppe": PickupLocationMailTokenService.pickup_location_messenger_group_link,
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
            "Solidarbeitrag - Betrag": "solidarity_contribution_amount",
            "Solidarbeitrag - Startdatum": "solidarity_contribution_start_date",
        }
        | TOKENS_COOP_ENTRY,
        required=True,
    )
    register_transactional_trigger(
        name="BestellWizard: Nur Geno-Mitgliedschaft",
        key=Events.REGISTER_MEMBERSHIP_ONLY,
        tokens=TOKENS_COOP_ENTRY,
        required=lambda: legal_status_is_cooperative(cache={}),
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
            "Solidarbeitrag - Betrag": "solidarity_contribution_amount",
            "Solidarbeitrag - Startdatum": "solidarity_contribution_start_date",
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

    register_transactional_trigger(
        name="Eintragung von Kündigung von Geno-Anteilen",
        key=Events.CANCELLATION_OF_COOP_SHARES,
        tokens={
            "Kündigungsdatum": "date_where_the_cancellation_was_triggered",
            "Wirksamkeitsdatum": "date_where_the_cancellation_is_active",
            "Anzahl der gekündigten Geno-Anteile": "number_of_cancelled_shares",
            "Wert eines Geno-Anteils": "value_of_a_single_share",
            "Gesamtwert gekündigte Geno-Anteile": "value_of_all_cancelled_shares",
        },
        required=lambda: legal_status_is_cooperative(cache={}),
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
