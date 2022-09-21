import distutils
from enum import Enum

from django.db import models


class TapirParameterDatatype(Enum):
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    STRING = "string"


class TapirParameter(models.Model):
    key = models.CharField(max_length=256, primary_key=True, editable=False)
    description = models.CharField(max_length=512)
    category = models.CharField(max_length=256)
    datatype = models.CharField(max_length=8, editable=False)
    value = models.CharField(max_length=4096, null=True)

    def get_value(self):
        if self.datatype == TapirParameterDatatype.INTEGER.value:
            return int(self.value)
        elif self.datatype == TapirParameterDatatype.DECIMAL.value:
            return float(self.value)
        elif self.datatype == TapirParameterDatatype.BOOLEAN.value:
            return bool(distutils.util.strtobool(self.value))
        elif self.datatype == TapirParameterDatatype.STRING.value:
            return self.value
        else:
            Exception("""Unknown parameter type: {}""".format(self.datatype))


class TapirParameterDefinitionImporter:
    def import_definitions(self):
        """Import the parameter definitions for the module."""
        pass
