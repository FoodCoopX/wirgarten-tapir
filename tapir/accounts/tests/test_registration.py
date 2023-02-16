from unittest import mock
from django_webtest import WebTest
from django.contrib.auth import get_user_model
from django.urls import reverse
from tapir.utils.tests_utils import KeycloakTestCase

User = get_user_model()


# FIXME
# class WizardTests(KeycloakTestCase, WebTest):
#    def test_simple_signup_flow(self):
#        self.has_ldap.return_value = False
#        self.ldap_save.return_value = None
#
#        form = self.app.get(reverse("wirgarten:draftuser_register")).form
#        form["Harvest Shares-harvest_shares_s"] = 1
#        r = form.submit()
#
#        form = r.form
#        form["Cooperative Shares-statute_consent"] = True
#        r = form.submit()
#
#        form = r.form
#        r = form.submit()
#
#        form = r.form
#        r = form.submit()
#
#        form = r.form
#        r = form.submit()
#
#        form = r.form
#        r = form.submit()
#
#        form = r.form
#        form["Personal Details-first_name"] = "Firstname"
#        form["Personal Details-last_name"] = "Lastname"
#        form["Personal Details-email"] = "any@mail.com"
#        form["Personal Details-phone_number"] = "+12125552368"
#        form["Personal Details-street"] = "fake street"
#        form["Personal Details-street_2"] = ""
#        form["Personal Details-postcode"] = "12345"
#        form["Personal Details-city"] = "Berlin"
#        form["Personal Details-country"] = "DE"
#        form["Personal Details-birthdate"] = ""
#        r = form.submit()
#
#        form = r.form
#        form["Payment Details-account_owner"] = "Firstname Lastname"
#        form["Payment Details-iban"] = "DE89370400440532013000"
#        form["Payment Details-bic"] = "DEUTDE5M"
#        r = form.submit()
#
#        form = r.form
#        form["Payment Details-sepa_consent"] = True
#        r = form.submit()
#
#        form = r.form
#        form["Consent-withdrawal_consent"] = True
#        form["Consent-privacy_consent"] = True
#        r = form.submit().follow()
#
#        user = User.objects.filter(email="any@mail.com").first()
#        self.assertIsNotNone(user)
