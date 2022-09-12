from enum import Enum

from django.core.exceptions import ObjectDoesNotExist

from tapir.configuration.models import Parameter, ParameterDatatype


def get_parameter_value(key: Enum):
    try:
        param = Parameter.objects.get(pk=key.value)
        return param.get_value()
    except ObjectDoesNotExist:
        raise KeyError(
            "Parameter with key {key.value} does not exist. Enum: {key}".format(key=key)
        )


def parameter_definition(
    key: Enum,
    description: str,
    category: str,
    datatype: ParameterDatatype,
    initial_value: str | int | float | bool,
):
    try:
        param = Parameter.objects.get(pk=key.value)
        param.description = description
        param.category = category
        param.datatype = datatype.value
        param.save()
    except ObjectDoesNotExist:
        Parameter.objects.create(
            key=key.value,
            description=description,
            category=category,
            datatype=datatype.value,
            value=str(initial_value),
        )
