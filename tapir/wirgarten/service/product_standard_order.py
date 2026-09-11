from django.db.models import Case, When, Value, IntegerField


def product_type_order_by(
    id_field: str = "id", name_field: str = "name", cache: dict | None = None
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

    from tapir.utils.services.tapir_cache import TapirCache

    try:
        return [
            Case(
                When(
                    **{
                        f"{id_field}__in": [
                            product_type.id
                            for product_type in TapirCache.get_all_product_types(
                                cache=cache
                            )
                            if product_type.must_be_subscribed_to
                        ]
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
