from django.conf import settings
from django.test import TestCase
import requests


class LdapBaseTestCase(TestCase):
    databases = '__all__'
    _old = {}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # basic setup. In the future this will be determined by the request itself.
        # only proof of concept
        requests.get('http://openldap:1000/start')
        cls._old = settings.DATABASES['ldap'].copy()
        settings.DATABASES['ldap']['USER'] = 'cn=testadmin,dc=lueneburg,dc=wirgarten,dc=com'
        settings.DATABASES['ldap']['PASSWORD'] = '7sYTyHOhEHrnOq8l6taa'
        settings.DATABASES['ldap']['NAME'] = 'ldap://openldap:5000'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        settings.DATABASES['ldap'] = cls._old
        requests.get('http://openldap:1000/stop')