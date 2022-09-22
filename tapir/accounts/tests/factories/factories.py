import factory

from tapir import settings
from tapir.accounts.models import TapirUser, LdapGroup
from tapir.accounts.tests.factories.user_data_factory import UserDataFactory


class TapirUserFactory(UserDataFactory):
    class Meta:
        model = TapirUser

    username = factory.LazyAttribute(lambda o: f"{o.first_name}.{o.last_name}")

    @factory.post_generation
    def password(self, create, password, **kwargs):
        if not create:
            return
        self.set_password(password or self.username)

    @factory.post_generation
    def is_in_member_office(self, create, is_in_member_office, **kwargs):
        if not create:
            return

        group_cn = settings.GROUP_MEMBER_OFFICE
        group = LdapGroup.objects.get(cn=group_cn)
        user_dn = self.get_ldap().build_dn()
        if is_in_member_office:
            group.members.append(user_dn)
            group.save()
        elif user_dn in group.members:
            # The current test setup uses the same LDAP server for all the tests, without resetting it in between tests,
            # so we have to make sure that this user has not been added to the member office by a previous test
            # or a previous run
            group.members.remove(user_dn)
            group.save()
