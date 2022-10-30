from tapir.wirgarten.classes import LdapBaseTestCase
from tapir.accounts.models import TapirUser, LdapPerson

#https://github.com/django-ldapdb/django-ldapdb/blob/master/examples/tests.py

class LdapEnabledTestCase(LdapBaseTestCase):
            
    def test_person_creation(self):
        pass
        #LdapPerson.objects.create(uid='asd', sn='sn', cn='cn')
        #self.assertTrue(LdapPerson.objects.filter(uid='asd'))
