from importlib.resources import _

from django import forms

from tapir.configuration.models import Parameter, ParameterDatatype


def create_field(param: Parameter):
    if param.datatype == ParameterDatatype.STRING.value:
        return forms.CharField(
            label=_(param.key),
            help_text=_(param.description),
            required=True,
            initial=param.value,
        )
    elif param.datatype == ParameterDatatype.INTEGER.value:
        return forms.IntegerField(
            label=_(param.key),
            help_text=_(param.description),
            required=True,
            initial=param.value,
        )
    elif param.datatype == ParameterDatatype.DECIMAL.value:
        return forms.DecimalField(
            label=_(param.key),
            help_text=_(param.description),
            required=True,
            initial=param.value,
        )
    elif param.datatype == ParameterDatatype.BOOLEAN.value:
        return forms.BooleanField(
            label=_(param.key),
            help_text=_(param.description),
            required=False,
            initial=param.value,
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

        params = Parameter.objects.order_by("category", "key")

        categories = list(set(map(lambda p: p.category, params)))
        categories.sort()

        self.categories = categories

        for param in params:
            print(param.__dict__)
            self.fields[param.key] = create_field(param)

        def get_category(name):
            for p in params:
                if p.key == name:
                    return p.category

        for visible in self.visible_fields():
            visible.category = get_category(visible.name)
