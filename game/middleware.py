from django.http import HttpResponseForbidden
import re

class SubdomainMiddleware:
    fbre = re.compile(r'^fb\.')
    def process_request(self, request):
        if request.is_secure():
            return HttpResponseForbidden()
        request.in_fb = bool(self.fbre.match(request.get_host()))
