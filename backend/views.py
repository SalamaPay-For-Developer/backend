from django.http import HttpResponse
from django.conf import settings


def api_home(request):
    status = "Operational" if not settings.DEBUG else "Development Mode"

    lines = [
        "SalamaPay API",
        "=============",
        "",
        f"Status: {status}",
        "Version: 1.0.0",
        "",
        "Copyright (c) 2026 SalamaPay. All rights reserved.",
    ]

    return HttpResponse("\n".join(lines), content_type="text/plain")
