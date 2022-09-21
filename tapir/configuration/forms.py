from importlib.resources import _

from django import forms

from tapir.configuration.models import TapirParameter, TapirParameterDatatype


def create_field(param: TapirParameter):
    if param.datatype == TapirParameterDatatype.STRING.value:
        return forms.CharField(
            label=_(param.key),
            help_text=_(param.description),
            required=True,
            initial=param.get_value(),
        )
    elif param.datatype == TapirParameterDatatype.INTEGER.value:
        return forms.IntegerField(
            label=_(param.key),
            help_text=_(param.description),
            required=True,
            initial=param.get_value(),
        )
    elif param.datatype == TapirParameterDatatype.DECIMAL.value:
        return forms.DecimalField(
            label=_(param.key),
            help_text=_(param.description),
            required=True,
            initial=param.get_value(),
        )
    elif param.datatype == TapirParameterDatatype.BOOLEAN.value:
        return forms.BooleanField(
            label=_(param.key),
            help_text=_(param.description),
            required=False,
            initial=param.get_value(),
        )
    else:
        NotImplementedError(
            """Unknown ParameterDatatype for parameter {param.key}: {param.datatype}""".format(
                param=param
            )
        )


class ParameterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ParameterForm, self).__init__(*args, **kwargs)

        params = TapirParameter.objects.order_by("category", "key")

        categories = list(set(map(lambda p: p.category, params)))
        categories.sort()

        self.categories = categories

        for param in params:
            self.fields[param.key] = create_field(param)

        def get_category(name):
            for p in params:
                if p.key == name:
                    return p.category

        for visible in self.visible_fields():
            visible.category = get_category(visible.name)
