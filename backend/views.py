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
        "Endpoints:",
        "  POST   /api/v1/accounts/register/     - Register a new account",
        "  POST   /api/v1/accounts/login/        - Login and get JWT tokens",
        "  POST   /api/v1/accounts/refresh/      - Refresh JWT token",
        "  GET    /api/v1/wallets/               - List wallets",
        "  GET    /api/v1/payments/transactions/ - List payment transactions",
        "  GET    /api/v1/payments/categories/   - List payment categories",
        "  GET    /api/v1/compliance/            - List compliance records",
        "  GET    /api/v1/modules/available/     - List available business modules",
        "  GET    /api/v1/modules/configs/       - List business module configs",
        "  POST   /api/v1/webhooks/selcom/       - Selcom webhook receiver",
        "",
        "Documentation:",
        "  /docs/        - Swagger UI",
        "  /redoc/       - ReDoc",
        "  /api/schema/  - OpenAPI Schema",
        "  /admin/       - Admin Panel",
        "",
        "SalamaPay (c) 2026",
    ]

    return HttpResponse("\n".join(lines), content_type="text/plain")
