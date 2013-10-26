from django.http import HttpResponseForbidden
from django.conf import settings
import re

class FacebookMiddleware:
    fbre = re.compile(r'^fb\.')
    def process_request(self, request):
        if request.is_secure():
            return HttpResponseForbidden()
        request.in_fb = bool(self.fbre.match(request.get_host()))

    def process_template_response(self, request, response):
        ctx = response.context_data
        ctx['FB_APP_ID'] = settings.FB_APP_ID
        ctx['in_fb'] = request.in_fb
        return response
