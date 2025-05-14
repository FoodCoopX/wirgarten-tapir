from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    Subscription,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.email import send_email
from tapir.wirgarten.service.member import send_order_confirmation
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_available_product_types,
    get_active_and_future_subscriptions,
    get_next_growing_period,
)
from tapir.wirgarten.tapirmail import Events
from tapir.wirgarten.utils import format_date, get_now, member_detail_url


@require_http_methods(["GET"])
@csrf_protect
@login_required
@transaction.atomic
def renew_contract_same_conditions(request, **kwargs):
    member_id = kwargs["pk"]
    new_subs = []
    cache = {}
    next_period = get_next_growing_period(cache=cache)

    available_product_types = [
        p.id
        for p in get_available_product_types(
            reference_date=next_period.start_date, cache=cache
        )
    ]

    for sub in get_active_subscriptions(cache=cache).filter(member_id=member_id):
        if sub.product.type.id in available_product_types:
            new_subs.append(
                Subscription(
                    member=sub.member,
                    product=sub.product,
                    period=next_period,
                    quantity=sub.quantity,
                    start_date=next_period.start_date,
                    end_date=next_period.end_date,
                    solidarity_price=sub.solidarity_price,
                    mandate_ref=sub.mandate_ref,
                )
            )
            # reset cancellation date on existing sub
            sub.cancellation_ts = None
            sub.save()
        else:
            print(
                f"[{sub.member.id}] Renew with same conditions. Skipping {sub.product.type.name} because there is no capacity or the product type was removed."
            )

    Subscription.objects.bulk_create(new_subs)

    member = Member.objects.get(id=member_id)
    member.sepa_consent = get_now(cache=cache)
    member.save()

    SubscriptionChangeLogEntry().populate(
        actor=request.user,
        user=member,
        change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.RENEWED,
        subscriptions=new_subs,
    ).save()

    send_order_confirmation(member, new_subs, cache=cache)

    return HttpResponseRedirect(member_detail_url(member_id))


@require_http_methods(["GET"])
@csrf_protect
@login_required
@transaction.atomic
def cancel_contract_at_period_end(request, **kwargs):
    member_id = kwargs["pk"]
    cache = {}
    now = get_now(cache=cache)
    subs = list(
        get_active_and_future_subscriptions(cache=cache).filter(
            member_id=member_id,
            period=GrowingPeriod.objects.get(start_date__lte=now, end_date__gte=now),
        )
    )
    for sub in subs:
        sub.cancellation_ts = now
        sub.save()

    end_date = subs[0].end_date

    member = Member.objects.get(id=member_id)

    SubscriptionChangeLogEntry().populate(
        actor=request.user,
        user=member,
        change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.NOT_RENEWED,
        subscriptions=subs,
    ).save()

    TransactionalTrigger.fire_action(
        key=Events.CONTRACT_NOT_RENEWED, recipient_email=member.email
    )

    # TODO: remove after tapir_mail migration
    send_email(
        to_email=[member.email],
        subject=get_parameter_value(
            ParameterKeys.EMAIL_NOT_RENEWED_CONFIRMATION_SUBJECT, cache=cache
        ),
        content=get_parameter_value(
            ParameterKeys.EMAIL_NOT_RENEWED_CONFIRMATION_CONTENT, cache=cache
        ),
        cache=cache,
    )

    return HttpResponseRedirect(
        member_detail_url(member_id) + "?notrenewed=" + format_date(end_date)
    )
