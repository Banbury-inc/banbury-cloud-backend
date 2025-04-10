from django.http import HttpResponse
from django.views import View
from django.conf import settings

class HealthCheckView(View):
    def get(self, request):
        return HttpResponse("OK", content_type="text/plain") 