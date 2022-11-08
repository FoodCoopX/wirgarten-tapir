from tapir.utils.tests_utils import LdapBaseTestCase
from tapir.accounts.models import TapirUser, LdapPerson

#https://github.com/django-ldapdb/django-ldapdb/blob/master/examples/tests.py


"""
class LdapEnabledTestCase(LdapBaseTestCase):
            
    def test_person_creation(self):
        LdapPerson.objects.create(uid='asd', sn='sn', cn='cn')
        self.assertTrue(LdapPerson.objects.filter(uid='asd'))


"""


#python manage.py test --testrunner="tapir.utils.tests_utils.UnitTestRunner" tapir.accounts.tests.test_ldap

class LdapTestCase(LdapBaseTestCase):
            
    def test_person_creation_one(self):
        LdapPerson.objects.create(uid='asd', sn='sn', cn='cn')
        self.assertTrue(LdapPerson.objects.filter(uid='asd'))
    
    def test_person_creation_two(self):
        LdapPerson.objects.create(uid='asd', sn='sn', cn='cn')
        self.assertTrue(LdapPerson.objects.filter(uid='asd'))
        



