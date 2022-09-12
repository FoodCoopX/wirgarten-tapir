from enum import Enum

from django.db import models


class ParameterDatatype(Enum):
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    STRING = "string"


class Parameter(models.Model):
    key = models.CharField(max_length=256, primary_key=True, editable=False)
    description = models.CharField(max_length=512)
    category = models.CharField(max_length=256)
    datatype = models.CharField(max_length=8, editable=False)
    value = models.CharField(max_length=4096, null=True)

    def get_value(self):
        if self.datatype == ParameterDatatype.INTEGER.value:
            return int(self.value)
        elif self.datatype == ParameterDatatype.DECIMAL.value:
            return float(self.value)
        elif self.datatype == ParameterDatatype.BOOLEAN.value:
            return bool(self.value)
        elif self.datatype == ParameterDatatype.STRING.value:
            return self.value
        else:
            Exception("""Unknown parameter type: {}""".format(self.datatype))
