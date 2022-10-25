from django import forms


class NoHarvestSharesForm(forms.Form):
    def is_valid(self):
        return True

    def __init__(self, *args, **kwargs):
        super(NoHarvestSharesForm, self).__init__(*args, **kwargs)
