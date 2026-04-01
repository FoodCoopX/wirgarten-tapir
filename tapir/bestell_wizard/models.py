from django.db import models

from tapir.core.models import TapirModel
from tapir.log.models import LogEntry
from tapir.wirgarten.models import CoopShareTransaction, ProductType


class ProductTypeAccordionInBestellWizard(TapirModel):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    description = models.TextField()
    order = models.IntegerField()
