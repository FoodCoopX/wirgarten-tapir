from django.db import connection


class JasminTenantMiddleware:
    """Activates Tapir's Jasmin tenant for the request, like django-tenants'
    TenantMainMiddleware does from the subdomain, see
    tapir.jasmin_integration.db_backend."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        connection.reset_tenant()
        request.tenant = connection.tenant
        return self.get_response(request)
