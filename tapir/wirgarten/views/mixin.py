from django.contrib.auth.mixins import PermissionRequiredMixin


class PermissionOrSelfRequiredMixin(PermissionRequiredMixin):
    def get_permission_required(self):
        return super(PermissionOrSelfRequiredMixin, self).get_permission_required()

    def has_permission(self):
        return self.request.user is not None and (
            self.request.user.pk == self.get_user_pk()
            or super(PermissionOrSelfRequiredMixin, self).has_permission()
        )

    def get_user_pk(self):
        return self.kwargs["pk"]
