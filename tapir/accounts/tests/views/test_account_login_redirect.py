from urllib.parse import parse_qs, urlparse

from django.test import SimpleTestCase
from django.urls import reverse


class TestAccountLoginRedirect(SimpleTestCase):
    def test_login_loginNextParam_isForwardedToKeycloakLogin(self):
        response = self.client.get(
            reverse("account_login"), {"next": "/bidding_rounds/?skip_intro=1"}
        )

        self.assertEqual(302, response.status_code)
        url = urlparse(response["Location"])
        self.assertEqual("/accounts/oidc/keycloak/login", url.path)
        self.assertEqual(["/bidding_rounds/?skip_intro=1"], parse_qs(url.query)["next"])

    def test_login_noNextParam_redirectsToKeycloakLogin(self):
        response = self.client.get(reverse("account_login"))

        self.assertEqual(302, response.status_code)
        self.assertEqual("/accounts/oidc/keycloak/login", response["Location"])
