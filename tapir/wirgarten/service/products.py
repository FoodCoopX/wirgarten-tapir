from datetime import date
from importlib.resources import _

from tapir.wirgarten.models import Subscription, ShareOwnership, MandateReference


def get_total_price_for_subs(subs: [Subscription]) -> float:
    """
    Returns the total amount of one payment for the given list of subs.

    :param subs: the list of subs (e.g. that are currently active for a user)
    :return: the total price in €
    """
    return round(
        sum(
            map(
                lambda x: get_total_price_for_sub_or_share_ownership(x),
                subs,
            )
        ),
        2,
    )


def get_total_price_for_sub_or_share_ownership(position: Subscription | ShareOwnership):
    """
    Gets the total price of one subscription or a share ownership.

    :param position: the subscription or share ownership instance
    :return: quantity * price of one unit
    """

    if type(position) == Subscription:
        position = {
            "quantity": position.quantity,
            "product": {
                "price": position.product.price,
            },
            "solidarity_price": position.solidarity_price,
        }
    elif type(position) == ShareOwnership:
        position = {
            "quantity": position.quantity,
            "product": {"price": position.share_price},
        }
    return (
        position["quantity"]
        * float(position["product"]["price"])
        * (1 + position.get("solidarity_price", 0.0))
    )


def get_subs_or_shares_for_mandate_ref(
    mandate_ref: MandateReference, reference_date: date
):
    subs = Subscription.objects.filter(
        mandate_ref=mandate_ref,
        start_date__lte=reference_date,
        end_date__gt=reference_date,
    )

    if subs.count() == 0:
        return list(
            map(
                lambda x: {
                    "amount": round(x.share_price, 2),
                    "quantity": x.quantity,
                    "product": {
                        "name": _("Genossenschaftsanteile"),
                        "price": x.share_price,
                    },
                },
                ShareOwnership.objects.filter(mandate_ref=mandate_ref),
            )
        )
    else:
        return subs
