from django.http import HttpResponse
from django.conf import settings


def api_home(request):
    status_class = "operational" if not settings.DEBUG else "development"
    status_text = "Operational" if not settings.DEBUG else "Development Mode"
    status_color = "#22c55e" if not settings.DEBUG else "#f59e0b"
    status_dot = "#16a34a" if not settings.DEBUG else "#d97706"

    endpoints = [
        {"method": "POST", "path": "/api/v1/accounts/register/", "desc": "Register a new account"},
        {"method": "POST", "path": "/api/v1/accounts/login/", "desc": "Login and get JWT tokens"},
        {"method": "POST", "path": "/api/v1/accounts/refresh/", "desc": "Refresh JWT token"},
        {"method": "GET", "path": "/api/v1/wallets/", "desc": "List wallets"},
        {"method": "GET", "path": "/api/v1/payments/transactions/", "desc": "List payment transactions"},
        {"method": "GET", "path": "/api/v1/payments/categories/", "desc": "List payment categories"},
        {"method": "GET", "path": "/api/v1/compliance/", "desc": "List compliance records"},
        {"method": "GET", "path": "/api/v1/modules/available/", "desc": "List available business modules"},
        {"method": "GET", "path": "/api/v1/modules/configs/", "desc": "List business module configs"},
        {"method": "POST", "path": "/api/v1/webhooks/selcom/", "desc": "Selcom webhook receiver"},
    ]

    endpoint_rows = ""
    for ep in endpoints:
        method_class = ep["method"].lower()
        endpoint_rows += f"""
        <tr>
            <td><span class="method method-{method_class}">{ep['method']}</span></td>
            <td><code>{ep['path']}</code></td>
            <td>{ep['desc']}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SalamaPay API</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }}
        .container {{
            max-width: 800px;
            width: 100%;
        }}
        .card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 3rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }}
        .logo {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }}
        .logo-icon {{
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 800;
            color: white;
        }}
        .logo h1 {{
            font-size: 1.75rem;
            font-weight: 700;
            color: #f8fafc;
        }}
        .tagline {{
            color: #94a3b8;
            font-size: 1rem;
            margin-bottom: 2rem;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba({', '.join(str(int(status_color[i:i+2], 16)) for i in (1, 3, 5))}, 0.15);
            border: 1px solid {status_color};
            color: {status_color};
            padding: 0.5rem 1rem;
            border-radius: 999px;
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 2rem;
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            background: {status_dot};
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}
        .section-title {{
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            margin-bottom: 1rem;
            margin-top: 2rem;
        }}
        .links {{
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-bottom: 0.5rem;
        }}
        .link-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.625rem 1.25rem;
            border-radius: 10px;
            font-size: 0.875rem;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s;
        }}
        .link-primary {{
            background: #3b82f6;
            color: white;
        }}
        .link-primary:hover {{
            background: #2563eb;
        }}
        .link-secondary {{
            background: #334155;
            color: #e2e8f0;
        }}
        .link-secondary:hover {{
            background: #475569;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 0.5rem;
        }}
        th {{
            text-align: left;
            padding: 0.75rem 0.5rem;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            border-bottom: 1px solid #334155;
        }}
        td {{
            padding: 0.75rem 0.5rem;
            border-bottom: 1px solid #1e293b;
            font-size: 0.875rem;
        }}
        td code {{
            background: #0f172a;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.8125rem;
            color: #93c5fd;
        }}
        .method {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
            min-width: 3rem;
            text-align: center;
        }}
        .method-get {{ background: #1e3a5f; color: #60a5fa; }}
        .method-post {{ background: #1e3a2f; color: #4ade80; }}
        .method-put {{ background: #3f3a1e; color: #fbbf24; }}
        .method-delete {{ background: #3f1e1e; color: #f87171; }}
        .footer {{
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid #334155;
            color: #64748b;
            font-size: 0.8125rem;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .version {{
            background: #334155;
            padding: 0.25rem 0.625rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            color: #94a3b8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="logo">
                <div class="logo-icon">S</div>
                <h1>SalamaPay API</h1>
            </div>
            <p class="tagline">One Wallet. One Card. One Platform. Pay Everything.</p>

            <div class="status-badge">
                <span class="status-dot"></span>
                All Systems {status_text}
            </div>

            <div class="section-title">Quick Links</div>
            <div class="links">
                <a href="/docs/" class="link-btn link-primary">
                    API Docs (Swagger)
                </a>
                <a href="/redoc/" class="link-btn link-secondary">
                    ReDoc
                </a>
                <a href="/admin/" class="link-btn link-secondary">
                    Admin Panel
                </a>
                <a href="/api/schema/" class="link-btn link-secondary">
                    OpenAPI Schema
                </a>
            </div>

            <div class="section-title">Available Endpoints</div>
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Endpoint</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {endpoint_rows}
                </tbody>
            </table>

            <div class="footer">
                <span>SalamaPay &copy; 2026 &middot; Mandatory Electronic Payments Compliance Platform</span>
                <span class="version">v1.0.0</span>
            </div>
        </div>
    </div>
</body>
</html>"""
    return HttpResponse(html, content_type="text/html")
