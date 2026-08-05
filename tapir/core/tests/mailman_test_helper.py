import unittest
from dataclasses import dataclass
from unittest.mock import patch, Mock

from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient


@dataclass
class MockMailingListData:
    name: str
    confirmed_recipients: list[str]
    unconfirmed_recipients: list[str]


class MailmanTestHelper:
    @classmethod
    def mock_domain(
        cls, test: unittest.TestCase, mailing_list_datas: list[MockMailingListData]
    ):
        if not hasattr(test, "mock_client"):
            patcher_client = patch.object(TapirMailmanClient, "get_client")
            test.mock_get_client = patcher_client.start()
            test.addCleanup(patcher_client.stop)

        client = Mock()
        test.mock_get_client.return_value = client
        domain = Mock()
        client.get_domain.return_value = domain
        domain.lists = [
            cls.build_mock_list(mailing_list) for mailing_list in mailing_list_datas
        ]

    @classmethod
    def build_mock_list(cls, mailing_list_data: MockMailingListData):
        mock_list = Mock()
        mock_list.fqdn_listname = mailing_list_data.name
        mock_list.members = [
            Mock(address=recipient)
            for recipient in mailing_list_data.confirmed_recipients
        ]
        mock_list.requests = [
            {"email": recipient}
            for recipient in mailing_list_data.unconfirmed_recipients
        ]
        return mock_list
