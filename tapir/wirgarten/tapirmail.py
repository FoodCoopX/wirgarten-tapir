from datetime import timedelta
from django.db import models
from tapir.wirgarten.service.products import get_next_growing_period
from tapir_mail.service.segment import (
    BASE_QUERYSET,
    register_base_segment,
    register_filter,
    register_segment,
)
from tapir_mail.service.token import register_tokens

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Member, PickupLocation
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.utils import get_today
from django.db.models import F, ExpressionWrapper
from django.db.models.functions import TruncMonth
from dateutil.relativedelta import relativedelta
from datetime import timedelta


def configure_mail_module():
    _register_segments()
    _register_filters()
    _register_tokens()
    _register_triggers()


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
        "Geno-Mitglieder",
        lambda: get_member_ids(shares_annotation, {"total_shares__gte": 1}),
    )
    register_segment(
        "Nicht Geno-Mitglieder",
        lambda: get_member_ids(shares_annotation, {"total_shares": 0}),
    )
    register_segment(
        "Mit laufendem Ertevertrag",
        lambda: get_member_ids(
            subscription_annotation, {"active_subscription_count__gte": 1}
        ),
    )
    register_segment(
        "Ohne laufendem Ertevertrag",
        lambda: get_member_ids(
            subscription_annotation, {"active_subscription_count": 0}
        ),
    )


def _register_filters():
    def create_contract_status_filter(expression):
        next_growing_period = get_next_growing_period()

        if next_growing_period is None:
            if expression == "no reaction":
                return lambda qs: qs.all()
            else:
                return lambda qs: qs.none()

        if expression == "yes":
            return lambda qs: qs.filter(
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

            return lambda qs: qs.annotate(
                trial_period_end=trial_period_end_expr
            ).filter(
                subscription__cancellation_ts__gt=F("trial_period_end"),
                subscription__cancellation_ts__isnull=False,
            )

        elif expression == "no reaction":
            trial_period_start = get_today() + relativedelta(months=-1, day=1)

            return (
                lambda qs: qs.filter(subscription__start_date__lte=trial_period_start)
                .exclude(subscription__cancellation_ts__isnull=False)
                .exclude(
                    subscription__start_date__gte=next_growing_period.start_date,
                    subscription__start_date__lte=next_growing_period.end_date,
                )
            )

    register_filter("Vertrag verlängert: ja", create_contract_status_filter("yes"))
    register_filter("Vertrag verlängert: nein", create_contract_status_filter("no"))
    register_filter(
        "Vertrag verlängert: keine Reaktion",
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
    # TODO
    pass
