from tapir.accounts.services.email_normaliser import EmailNormaliser
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestEmailNormaliser(TapirUnitTest):
    def test_normalise_emptyString_returnsEmptyString(self):
        result = EmailNormaliser.normalise("")

        self.assertEqual("", result)

    def test_normalise_onlyWhitespace_returnsEmptyString(self):
        result = EmailNormaliser.normalise("\n\t  \r")

        self.assertEqual("", result)

    def test_normalise_emailAddressWithWhitespacesAndUppercase_returnsNormalisedAddress(
        self,
    ):
        result = EmailNormaliser.normalise("\tteSt@eXample.cOm   ")

        self.assertEqual("test@example.com", result)
