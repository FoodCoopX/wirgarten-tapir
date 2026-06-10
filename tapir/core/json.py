import json
from typing import Any

from django.db import models
from django.forms import model_to_dict
from django.core.serializers.json import DjangoJSONEncoder
from phonenumber_field.phonenumber import PhoneNumber


class LazyEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, models.Model):  # use django serializer
            return model_to_dict(obj)

        if isinstance(obj, PhoneNumber):
            if obj.country_code == 49:  # german number
                return obj.as_national
            return obj.as_international

        return super().default(obj)


def dumps_with_encoder(obj: Any):
    return json.dumps(obj, cls=LazyEncoder)
