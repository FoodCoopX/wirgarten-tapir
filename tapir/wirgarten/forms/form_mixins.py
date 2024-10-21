from icecream import ic


class FormWithRequestMixin:
    def __init__(self, *args, **kwargs):
        ic("FormWithRequestMixin init")
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
