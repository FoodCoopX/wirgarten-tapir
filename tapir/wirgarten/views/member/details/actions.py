from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.automatic_solidarity_contribution_renewal_service import (
    AutomaticSolidarityContributionRenewalService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.services.tapir_cache_manager import TapirCacheManager
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    Subscription,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.service.member import send_product_order_confirmation
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_available_product_types,
    get_active_and_future_subscriptions,
    get_next_growing_period,
)
from tapir.wirgarten.utils import format_date, get_now, member_detail_url, get_today


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

    TapirCacheManager.clear_category(cache=cache, category="subscriptions")

    member = Member.objects.get(id=member_id)
    member.sepa_consent = get_now(cache=cache)
    member.save()

    SubscriptionChangeLogEntry().populate_subscription_changed(
        actor=request.user,
        user=member,
        change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.RENEWED,
        subscriptions=new_subs,
        admin_confirmed=get_now(cache=cache),
    ).save()

    renew_solidarity_contribution_if_necessary(member_id=member_id, cache=cache)

    send_product_order_confirmation(
        member,
        new_subs,
        cache=cache,
        from_waiting_list=False,
        coop_share_transaction=None,
    )

    return HttpResponseRedirect(member_detail_url(member_id))


def renew_solidarity_contribution_if_necessary(member_id: str, cache: dict):
    current_growing_period = TapirCache.get_growing_period_at_date(
        reference_date=get_today(cache), cache=cache
    )
    current_contribution = SolidarityContribution.objects.filter(
        member_id=member_id,
        start_date__lte=current_growing_period.end_date,
        end_date__gte=current_growing_period.end_date,
    ).first()
    future_contribution = SolidarityContribution.objects.filter(
        member_id=member_id,
        start_date__gt=current_growing_period.end_date,
    ).first()
    if current_contribution is not None and future_contribution is None:
        renewed_contribution = (
            AutomaticSolidarityContributionRenewalService.build_renewed_contribution(
                contribution=current_contribution, cache=cache
            )
        )
        renewed_contribution.save()


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

    SubscriptionChangeLogEntry().populate_subscription_changed(
        actor=request.user,
        user=member,
        change_type=SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.NOT_RENEWED,
        subscriptions=subs,
        admin_confirmed=now,
    ).save()

    TransactionalTrigger.fire_action(
        TransactionalTriggerData(
            key=Events.CONTRACT_NOT_RENEWED,
            recipient_id_in_base_queryset=member.id,
        ),
    )

    return HttpResponseRedirect(
        member_detail_url(member_id) + "?notrenewed=" + format_date(end_date)
    )
