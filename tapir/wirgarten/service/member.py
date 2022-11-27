from django.db import transaction

from tapir.wirgarten.models import ShareOwnership, TransferCoopSharesLogEntry


@transaction.atomic
def transfer_coop_shares(origin_member, target_member, quantity, actor):
    origin_ownership = ShareOwnership.objects.get(member_id=origin_member)

    if quantity < 1:
        return False  # nothing to do

    # if quantity exceeds origin shares, just take all shares
    if quantity > origin_ownership.quantity:
        quantity = origin_ownership.quantity

    try:
        target_ownership = ShareOwnership.objects.get(member_id=target_member)
        target_ownership.quantity += quantity
        target_ownership.save()
    except ShareOwnership.DoesNotExist:
        target_ownership = ShareOwnership.objects.create(
            member_id=target_member,
            quantity=quantity,
            share_price=origin_ownership.share_price,
        )

    # TODO: can we delete the ShareOwnership if quantity == 0 ?
    origin_ownership.quantity -= quantity
    origin_ownership.save()

    TransferCoopSharesLogEntry().populate(
        actor=actor,
        user=origin_ownership.member,
        target_member=target_ownership.member,
        quantity=quantity,
    ).save()
