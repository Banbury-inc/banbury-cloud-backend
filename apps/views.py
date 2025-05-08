from django.shortcuts import render
import os


def homepage(request):
    service = os.environ.get("K_SERVICE", "Unknown service")
    revision = os.environ.get("K_REVISION", "Unknown revision")

    return render(
        request,
        "homepage.html",
        context={
            "message": "It's running!",
            "Service": service,
            "Revision": revision,
        },
    )
