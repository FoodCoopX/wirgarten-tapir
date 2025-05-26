from typing import Dict

from django import forms
from django.forms import Textarea
from django.utils.translation import gettext_lazy as _

from tapir.configuration.models import TapirParameter, TapirParameterDatatype
from tapir.configuration.parameter import (
    get_parameter_meta,
)
from tapir.configuration.templatetags.configuration import tokenize_parameter
from tapir.utils.forms import DateInput
from tapir.wirgarten.utils import is_debug_instance


def create_field(param: TapirParameter, cache: Dict):
    description = f"""<span name="param-key" style="display:none">{param.key}</span>{_(param.description)}"""

    param_meta = get_parameter_meta(param.key)
    if param_meta is None:
        return None

    if param_meta.show_only_when is not None and not param_meta.show_only_when(cache):
        return None
    param_value = param.get_value()

    help_text = description
    if param_meta.vars_hint:
        vars_sorted = map(lambda x: "{" + x + "}", sorted(param_meta.vars_hint))
        help_text += f"""<br/><small><strong>Variablen:</strong> {", ".join(vars_sorted)}</small>"""
    help_text = tokenize_parameter(help_text, cache=cache)

    options = param_meta.options
    if param_meta.options_callable is not None:
        options = param_meta.options_callable()

    if options is not None and len(options) > 0:
        return forms.ChoiceField(
            label=_(param.label),
            help_text=help_text,
            choices=options,
            required=True,
            initial=param_value,
            validators=param_meta.validators,
            disabled=not param.enabled,
        )
    elif param.datatype == TapirParameterDatatype.STRING.value:
        return forms.CharField(
            label=_(param.label),
            help_text=help_text,
            required=True,
            initial=param_value,
            validators=param_meta.validators,
            widget=Textarea if param_meta.textarea else None,
            disabled=not param.enabled,
        )
    elif param.datatype == TapirParameterDatatype.INTEGER.value:
        return forms.IntegerField(
            label=_(param.label),
            help_text=help_text,
            required=True,
            initial=param_value,
            validators=param_meta.validators,
            disabled=not param.enabled,
        )
    elif param.datatype == TapirParameterDatatype.DECIMAL.value:
        return forms.DecimalField(
            label=_(param.label),
            help_text=help_text,
            required=True,
            initial=param_value,
            validators=param_meta.validators,
            disabled=not param.enabled,
        )
    elif param.datatype == TapirParameterDatatype.BOOLEAN.value:
        return forms.BooleanField(
            label=_(param.label),
            help_text=help_text,
            required=False,
            initial=param_value,
            validators=param_meta.validators,
            disabled=not param.enabled,
        )
    elif param.datatype == TapirParameterDatatype.DATE.value:
        return forms.DateField(
            label=_(param.label),
            help_text=help_text,
            required=False,
            initial=param_value,
            validators=param_meta.validators,
            disabled=not param.enabled,
            widget=DateInput,
        )
    else:
        raise NotImplementedError(
            """Unknown ParameterDatatype for parameter {param.key}: {param.datatype}""".format(
                param=param
            )
        )


class ParameterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ParameterForm, self).__init__(*args, **kwargs)

        params = TapirParameter.objects.order_by("category", "-order_priority", "key")

        if not is_debug_instance():
            params = params.filter(debug=False)

        cache = {}

        categories = list(set(map(lambda p: p.category, params)))
        categories.sort(key=lambda category: tokenize_parameter(category, cache=cache))

        self.categories = categories

        for param in params:
            field = create_field(param, cache=cache)
            if field is not None:
                self.fields[param.key] = field

        def get_category(name):
            for p in params:
                if p.key == name:
                    return p.category

        for visible in self.visible_fields():
            visible.category = get_category(visible.name)
