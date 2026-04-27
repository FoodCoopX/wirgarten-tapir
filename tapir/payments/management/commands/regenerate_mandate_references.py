from django.core.management import BaseCommand
from django.db import transaction

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys


class Command(BaseCommand):
    help = (
        "For every member, compares a newly generated MandateReference with the current one and, if different, saves the new one. "
        "If the reference contains a random part, that means a new reference will be generated for all members. "
        "This command is useful if the parameter PAYMENT_MANDATE_REFERENCE_PATTERN gets changed."
    )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        cache = {}
        for member in Member.objects.all():
            old_reference = MandateReferenceProvider.get_or_create_mandate_reference(
                member=member, cache=cache
            ).ref

            new_reference = MandateReferenceProvider.build_mandate_ref(
                member=member,
                pattern=get_parameter_value(
                    key=ParameterKeys.PAYMENT_MANDATE_REFERENCE_PATTERN, cache=cache
                ),
            )
            if old_reference == new_reference:
                continue

            MandateReferenceProvider.create_mandate_ref(member=member, cache=cache)
