from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestLoginRedirect(TapirUnitTest):
    def test_accountLogin_preservesNext(self):
        response = self.client.get(
            "/accounts/login/", {"next": "/bidding_rounds/?skip_intro=1"}
        )

        self.assertEqual(302, response.status_code)
        self.assertTrue(
            response.url.startswith("/accounts/oidc/keycloak/login?"),
            response.url,
        )
        self.assertIn(
            "next=%2Fbidding_rounds%2F%3Fskip_intro%3D1",
            response.url,
        )

    def test_accountLogin_dropsUnknownParameters(self):
        response = self.client.get(
            "/accounts/login/",
            {"next": "/bidding_rounds/", "kc_action": "delete_account"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("next=%2Fbidding_rounds%2F", response.url)
        self.assertNotIn("kc_action", response.url)
