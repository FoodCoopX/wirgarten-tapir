from urllib.parse import urlparse, parse_qs

from django.test import SimpleTestCase, override_settings, RequestFactory

from tapir.accounts.views import PasswordChangeRedirectView


@override_settings(
    KEYCLOAK_ADMIN_CONFIG={
        "PUBLIC_URL": "https://auth.example.org/",
        "REALM_NAME": "tapir-test",
        "FRONTEND_CLIENT_ID": "tapir-frontend",
    }
)
class TestPasswordChangeRedirectView(SimpleTestCase):
    def get_redirect(self):
        request = RequestFactory().get(
            "/accounts/password_change", HTTP_HOST="tapir.example.org", secure=True
        )
        return PasswordChangeRedirectView.as_view()(request)

    def test_get_default_redirectsToKeycloakUpdatePasswordAction(self):
        response = self.get_redirect()

        self.assertEqual(302, response.status_code)
        url = urlparse(response["Location"])
        self.assertEqual("https", url.scheme)
        self.assertEqual("auth.example.org", url.netloc)
        self.assertEqual("/realms/tapir-test/protocol/openid-connect/auth", url.path)
        params = parse_qs(url.query)
        self.assertEqual(["UPDATE_PASSWORD"], params["kc_action"])
        self.assertEqual(["tapir-frontend"], params["client_id"])
        self.assertEqual(["code"], params["response_type"])
        self.assertEqual(["openid"], params["scope"])
        self.assertEqual(
            ["https://tapir.example.org/?passwordchanged=true"],
            params["redirect_uri"],
        )

    def test_get_twoRequests_stateIsRandom(self):
        state_1 = parse_qs(urlparse(self.get_redirect()["Location"]).query)["state"]
        state_2 = parse_qs(urlparse(self.get_redirect()["Location"]).query)["state"]

        self.assertNotEqual(state_1, state_2)
