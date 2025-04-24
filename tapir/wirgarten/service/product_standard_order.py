from typing import Dict

from django.db.models import Case, When, Value, IntegerField

from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)


def product_type_order_by(
    id_field: str = "id", name_field: str = "name", cache: Dict | None = None
):
    """
    The result of the function is meant to be passed to the order_by clause of QuerySets referencing
    (directly or indirectly) product types.
    The base product type which is configured via parameter is the first result. In case the parameter is not there,
    only the name field will be used to order.

    It is basically a workaround to use this order by condition in a static way,
    although it depends on the parameter to be there.

    :param id_field: name/path of the "id" field. E.g. "product_type__id"
    :param name_field: name/path of the "name" field. E.g. "product_type__name"
    :return: an array of order conditions
    """

    try:
        return [
            Case(
                When(
                    **{
                        id_field: BaseProductTypeService.get_base_product_type(
                            cache=cache
                        ).id
                    },
                    then=Value(0),
                ),
                default=1,
                output_field=IntegerField(),
            ),
            name_field,
        ]
    except BaseException:
        return [name_field]
