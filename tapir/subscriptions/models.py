from django.db import models

from tapir.wirgarten.models import ProductType, GrowingPeriod


class NoticePeriod(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    growing_period = models.ForeignKey(GrowingPeriod, on_delete=models.CASCADE)
    duration = (
        models.IntegerField()
    )  # can be weeks or months depending on ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT
