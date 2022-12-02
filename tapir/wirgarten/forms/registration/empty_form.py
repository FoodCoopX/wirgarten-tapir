from django import forms


class EmptyForm(forms.Form):
    def is_valid(self):
        return True

    def __init__(self, *args, **kwargs):
        super(EmptyForm, self).__init__(*args, **kwargs)
