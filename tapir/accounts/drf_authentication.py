from rest_framework import authentication


class DrfForwardAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request._request.user.is_authenticated:
            return (request._request.user, None)
        return None
