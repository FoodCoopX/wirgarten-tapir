from django.core.exceptions import ObjectDoesNotExist

from tapir.configuration.models import TapirParameter, TapirParameterDatatype


def get_parameter_value(key: str):
    try:
        param = TapirParameter.objects.get(pk=key)
        return param.get_value()
    except ObjectDoesNotExist:
        raise KeyError("Parameter with key '{key}' does not exist.".format(key=key))


def parameter_definition(
    key: str,
    label: str,
    description: str,
    category: str,
    datatype: TapirParameterDatatype,
    initial_value: str | int | float | bool,
):
    try:
        if type(initial_value) == str:
            assert datatype == TapirParameterDatatype.STRING
        elif type(initial_value) == int:
            assert datatype == TapirParameterDatatype.INTEGER
        elif type(initial_value) == float:
            assert datatype == TapirParameterDatatype.DECIMAL
        elif type(initial_value) == bool:
            assert datatype == TapirParameterDatatype.BOOLEAN
    except AssertionError:
        raise TypeError(
            "Parameter '{key}' is defined with datatype '{datatype}', but the initial value is of type '{actual_type}': {value}".format(
                key=key,
                datatype=datatype,
                value=initial_value,
                actual_type=type(initial_value),
            )
        )

    try:
        param = TapirParameter.objects.get(pk=key)
        param.label = label
        param.description = description
        param.category = category
        param.datatype = datatype.value

        print("\t[update] ", key)

        param.save()
    except ObjectDoesNotExist:
        print("\t[create] ", key)

        TapirParameter.objects.create(
            key=key,
            label=label,
            description=description,
            category=category,
            datatype=datatype.value,
            value=str(initial_value),
        )
