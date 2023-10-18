from django.db.models import Case, F, IntegerField, Sum, When
from tapir_mail.service.segment import (
    BASE_QUERYSET,
    register_base_segment,
    register_filter,
    register_segment,
)
from tapir_mail.service.token import register_tokens

from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today


def configure_mail_module():
    _register_segments()
    _register_filters()
    _register_tokens()
    _register_triggers()


def _register_segments():
    register_base_segment(Member.objects.all())

    register_segment(
        "Geno-Mitglieder",
        lambda: Member.objects.filter(
            id__in=Member.objects.annotate(
                total_shares=Sum(
                    Case(
                        When(
                            coopsharetransaction__valid_at__lte=get_today(),
                            then=F("coopsharetransaction__quantity"),
                        ),
                        default=0,
                        output_field=IntegerField(),
                    )
                )
            )
            .filter(total_shares__gte=1)
            .values_list("id", flat=True)
        ),
    )

    register_segment(
        "Nicht Geno-Mitglieder",
        lambda: Member.objects.filter(
            id__in=Member.objects.annotate(
                total_shares=Sum(
                    Case(
                        When(
                            coopsharetransaction__valid_at__lte=get_today(),
                            then=F("coopsharetransaction__quantity"),
                        ),
                        default=0,
                        output_field=IntegerField(),
                    )
                )
            )
            .filter(total_shares=0)
            .values_list("id", flat=True)
        ),
    )

    # TODO
    # register_segment(Member.objects.filter(), "Mit laufendem Ertevertrag")
    # register_segment(Member.objects.filter(), "Kein laufender Ertevertrag")


def _register_filters():
    # TODO
    pass


def _register_tokens():
    # TODO:
    # register_tokens(
    #    user_tokens={
    #        "Vorname": "first_name",
    #        "Nachname": "last_name",
    #        "Email": "email",
    #        "Abholort": "pickup_location",
    #        "Ernteanteilsgröße": "subscription_type",
    #    },
    #    general_tokens={
    #        "WirGarten Standort": lambda: "WirGarten Lüneburg eG",
    #        "Admin Name": "Max Mustermann",
    #        "Admin Email": "max.mustermann@example.com",
    #    },
    # )
    pass


def _register_triggers():
    # TODO
    pass
