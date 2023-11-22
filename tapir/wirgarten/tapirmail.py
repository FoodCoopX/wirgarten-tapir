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
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import get_next_growing_period
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


class Segments:
    COOP_MEMBERS = "Geno-Mitglieder"
    NON_COOP_MEMBERS = "Nicht Geno-Mitglieder"
    WITH_ACTIVE_SUBSCRIPTION = "Mit laufendem Ertevertrag"
    WITHOUT_ACTIVE_SUBSCRIPTION = "Ohne laufendem Ertevertrag"


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

    def get_member_ids(annotation, filter_condition):
        return base.filter(
            id__in=Member.objects.annotate(**annotation)
            .filter(**filter_condition)
            .values_list("id", flat=True)
        )

    shares_annotation = {
        "total_shares": models.Sum(
            models.Case(
                models.When(
                    coopsharetransaction__valid_at__lte=get_today(),
                    then=models.F("coopsharetransaction__quantity"),
                ),
                default=0,
                output_field=models.IntegerField(),
            )
        )
    }

    subscription_annotation = {
        "active_subscription_count": models.Count(
            models.Case(
                models.When(
                    subscription__start_date__lte=get_today(),
                    subscription__end_date__gte=get_today(),
                    then=1,
                ),
                output_field=models.IntegerField(),
            )
        )
    }

    register_segment(
        Segments.COOP_MEMBERS,
        lambda: get_member_ids(shares_annotation, {"total_shares__gte": 1}),
    )
    register_segment(
        Segments.NON_COOP_MEMBERS,
        lambda: get_member_ids(shares_annotation, {"total_shares": 0}),
    )
    register_segment(
        Segments.WITH_ACTIVE_SUBSCRIPTION,
        lambda: get_member_ids(
            subscription_annotation, {"active_subscription_count__gte": 1}
        ),
    )
    register_segment(
        Segments.WITHOUT_ACTIVE_SUBSCRIPTION,
        lambda: get_member_ids(
            subscription_annotation, {"active_subscription_count": 0}
        ),
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
        },
        general_tokens={
            "WirGarten Standort": lambda: get_parameter_value(Parameter.SITE_NAME),
            "Admin Name": lambda: get_parameter_value(Parameter.SITE_ADMIN_NAME),
            "Admin Email": lambda: get_parameter_value(Parameter.SITE_ADMIN_EMAIL),
            "Admin Telefonnr": lambda: get_parameter_value(
                Parameter.SITE_ADMIN_TELEPHONE
            ),
            "Admin Image": lambda: get_parameter_value(Parameter.SITE_ADMIN_IMAGE),
            "Kontakt Email": lambda: get_parameter_value(Parameter.SITE_EMAIL),
            "Datenschutzerklärung Link": lambda: get_parameter_value(
                Parameter.SITE_PRIVACY_LINK
            ),
            "Mitglieder-FAQ Link": lambda: get_parameter_value(Parameter.SITE_FAQ_LINK),
            "Satzung Link": lambda: get_parameter_value(Parameter.COOP_STATUTE_LINK),
            "Infos zur Genossenschaft": lambda: get_parameter_value(
                Parameter.COOP_INFO_LINK
            ),
            "Jahr (aktuell)": lambda: get_today().year,
            "Jahr (nächstes)": lambda: get_today().year + 1,
            "Jahr (übernächstes)": lambda: get_today().year + 2,
        },
    )
    pass


def _register_triggers():
    TransactionalTrigger.register_action(
        "BestellWizard: Mitgliedschaft + Ernteanteile",
        Events.REGISTER_MEMBERSHIP_AND_SUBSCRIPTION,
    )
    TransactionalTrigger.register_action(
        "BestellWizard: Nur Geno-Mitgliedschaft", Events.REGISTER_MEMBERSHIP_ONLY
    )
    TransactionalTrigger.register_action(
        "Vertragsänderungen im Mitgliederbereich", Events.MEMBERAREA_CHANGE_CONTRACT
    )
    TransactionalTrigger.register_action(
        "Mitgliedsdatenänderungen", Events.MEMBERAREA_CHANGE_DATA
    )

    register_trigger(OnboardingTrigger)


def synchronize_waitlist_segment_for_entry(entry):
    static_segment, _ = StaticSegment.objects.get_or_create(
        name=f"Warteliste: {entry.get_type_display()}"
    )

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
    for recipient in StaticSegmentRecipient.objects.all():
        if not WaitingListEntry.objects.filter(email=recipient.email).exists():
            recipient.delete()


@receiver(post_save, sender=WaitingListEntry)
def create_or_update_recipient(sender, instance, created, **kwargs):
    synchronize_waitlist_segment_for_entry(instance)


@receiver(post_delete, sender=WaitingListEntry)
def delete_recipient(sender, instance, **kwargs):
    try:
        static_segment = StaticSegment.objects.get(
            name=f"Warteliste: {instance.get_type_display()}"
        )
        recipient = StaticSegmentRecipient.objects.get(
            segment=static_segment, email=instance.email
        )
        recipient.delete()
    except (StaticSegment.DoesNotExist, StaticSegmentRecipient.DoesNotExist):
        pass
