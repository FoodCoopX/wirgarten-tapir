import re
from typing import Dict

from django.core.exceptions import ObjectDoesNotExist, ValidationError

from tapir.configuration.models import (
    TapirParameter,
    TapirParameterDatatype,
    TapirParameterDefinitionImporter,
)
from tapir.utils.shortcuts import get_from_cache_or_compute


def validate_format_string(value: str, allowed_vars: [str]):
    """
    Validates if a string with potential format brackets (e.g.: "{some_variable}") only uses variables from the given array of known vars.

    :param value: the string to validate
    :param allowed_vars: the array of known variables.
    """

    for match in re.findall("{[^{}]*}", f"{value}"):
        match = match[1 : len(match) - 1].strip()  # strip brackets
        match = match.split(".")[
            0
        ].strip()  # if object, use only the part before the first dot
        if match not in allowed_vars:
            raise ValidationError(
                f"Unknown variable '{match}'! Known variables: {allowed_vars}"
            )


class ParameterMeta:
    def __init__(
        self,
        options: [tuple] = None,
        validators: [callable] = [],
        textarea=False,
        vars_hint: [str] = None,
    ):
        if vars_hint is not None and len(vars_hint) > 0:
            validators += [lambda x: validate_format_string(x, vars_hint)]

        self.vars_hint = vars_hint
        self.options = options
        self.validators = validators
        self.textarea = textarea


class ParameterMetaInfo:
    parameters = {str: ParameterMeta}
    initialized = False

    def initialize(self):
        for cls in TapirParameterDefinitionImporter.__subclasses__():
            cls.import_definitions(cls)
        self.initialized = True


meta_info = ParameterMetaInfo()


def get_parameter_meta(key: str) -> ParameterMeta | None:
    if not meta_info.initialized:
        meta_info.initialize()

    if key not in meta_info.parameters:
        print("\t[delete] ", key)
        TapirParameter.objects.get(key=key).delete()
        return None

    return meta_info.parameters[key]


def get_parameter_value(key: str, cache: Dict | None = None):
    def compute():
        tapir_parameter = TapirParameter.objects.filter(key=key).first()
        if tapir_parameter is None:
            raise KeyError("Parameter with key '{key}' does not exist.".format(key=key))
        return tapir_parameter.get_value()

    return get_from_cache_or_compute(cache, key, compute)


def parameter_definition(
    key: str,
    label: str,
    description: str,
    category: str,
    datatype: TapirParameterDatatype,
    initial_value: str | int | float | bool,
    order_priority: int = -1,
    meta: ParameterMeta = ParameterMeta(
        options=None, validators=[], vars_hint=None, textarea=False
    ),
):
    __validate_initial_value(datatype, initial_value, key, meta.validators)

    param = __create_or_update_parameter(
        category,
        datatype,
        description,
        initial_value,
        key,
        label,
        order_priority,
    )

    meta_info.parameters[param.key] = meta


def __create_or_update_parameter(
    category,
    datatype,
    description,
    initial_value,
    key,
    label,
    order_priority,
):
    try:
        param = TapirParameter.objects.get(pk=key)
        param.label = label
        param.description = description
        param.category = category
        if param.datatype != datatype.value:
            param.datatype = datatype.value
            param.value = initial_value  # only update value with initial value if the datatype changed!

        param.order_priority = order_priority

        # print("\t[update] ", key)

        param.save()
    except ObjectDoesNotExist:
        # print("******* [create] ", key)

        param = TapirParameter.objects.create(
            key=key,
            label=label,
            description=description,
            category=category,
            order_priority=order_priority,
            datatype=datatype.value,
            value=str(initial_value),
        )

    return param


def __validate_initial_value(datatype, initial_value, key, validators):
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
            "Parameter '{key}' is defined with datatype '{datatype}', \
            but the initial value is of type '{actual_type}': {value}".format(
                key=key,
                datatype=datatype,
                value=initial_value,
                actual_type=type(initial_value),
            )
        )

    for validator in validators:
        validator(initial_value)
