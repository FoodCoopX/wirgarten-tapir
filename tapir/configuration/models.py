from enum import Enum

from django.db import models


class TapirParameterDatatype(Enum):
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    STRING = "string"


class TapirParameter(models.Model):
    key = models.CharField(max_length=256, primary_key=True, editable=False)
    label = models.CharField(max_length=256, null=False)
    description = models.CharField(max_length=512)
    category = models.CharField(max_length=256)
    datatype = models.CharField(max_length=8)
    order_priority = models.IntegerField(null=False, default=-1)
    value = models.CharField(max_length=4096, null=True)
    options: [tuple] = None
    validators: [callable] = []

    def full_clean(self):
        for validator in self.validators:
            validator(self.value)

    def get_value(self):
        if self.datatype == TapirParameterDatatype.INTEGER.value:
            return int(self.value)
        elif self.datatype == TapirParameterDatatype.DECIMAL.value:
            return float(self.value)
        elif self.datatype == TapirParameterDatatype.BOOLEAN.value:
            return bool(self.str2bool(self.value))
        elif self.datatype == TapirParameterDatatype.STRING.value:
            return self.value
        else:
            raise TypeError("""Unknown parameter type: {}""".format(self.datatype))

    @staticmethod
    def str2bool(value: str):
        value = value.lower()
        if value in {"yes", "true", "t", "y", "1"}:
            return True
        if value in {"no", "false", "f", "n", "0"}:
            return False

        raise ValueError(f"Could not convert value '{value}' to bool")


class TapirParameterDefinitionImporter:
    def import_definitions(self, skip_validation: bool = False):
        """Import the parameter definitions for the module."""
        pass
