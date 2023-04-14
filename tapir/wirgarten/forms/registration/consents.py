from django.utils.translation import gettext_lazy as _

from django import forms

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameters import Parameter


class ConsentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ConsentForm, self).__init__(*args, **kwargs)

        self.fields["withdrawal_consent"] = forms.BooleanField(
            label=_("Ja, ich habe die Widerrufsbelehrung zur Kenntnis genommen."),
            required=True,
            help_text=_(
                'Du kannst deine Verträge und Beitrittserklärung innerhalb von zwei Wochen in Textform (z.B. Brief, E-Mail) widerrufen. Die Frist beginnt spätestens mit Erhalt dieser Belehrung. Zur Wahrung der Widerrufsfrist genügt die rechtzeitige Absendung eines formlosen Widerrufsschreibens an <a target="_blank" href="mailto:{site_email}">{site_email}</a>.'
            ).format(site_email=get_parameter_value(Parameter.SITE_EMAIL)),
        )

        self.fields["privacy_consent"] = forms.BooleanField(
            label=_("Ja, ich habe die Datenschutzerklärung zur Kenntnis genommen."),
            required=True,
            help_text=_(
                'Wir behandeln deine Daten vertraulich, verwenden diese nur im Rahmen der Mitgliederverwaltung und geben sie nicht an Dritte weiter. Unsere Datenschutzerklärung kannst du hier einsehen: <a target="_blank" href="{privacy_link}">Datenschutzerklärung - {site_name}</a>'
            ).format(
                site_name=get_parameter_value(Parameter.SITE_NAME),
                privacy_link=get_parameter_value(Parameter.SITE_PRIVACY_LINK),
            ),
        )
