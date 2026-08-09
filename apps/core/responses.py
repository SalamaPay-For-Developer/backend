"""
Standard API response envelope used across all SalamaPay v1 endpoints.

Success:
    {"status": "success", "code": 200, "data": {...}}

Error:
    {"status": "error", "code": 400, "error_code": "validation_error", "message": "..."}
"""
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def success_response(data=None, code=200):
    return Response({
        "status": "success",
        "code": code,
        "data": data if data is not None else {},
    }, status=code)


def error_response(message, code=400, error_code="validation_error"):
    return Response({
        "status": "error",
        "code": code,
        "error_code": error_code,
        "message": message,
    }, status=code)


def envelope_exception_handler(exc, context):
    """
    DRF custom exception handler that wraps every error response
    (validation errors, auth errors, throttling, etc.) in the standard
    SalamaPay error envelope.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    error_code_map = {
        400: "validation_error",
        401: "unauthorized",
        403: "insufficient_scope",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_error",
    }

    detail = response.data
    if isinstance(detail, dict):
        message = detail.get("detail") or "; ".join(
            f"{k}: {v[0] if isinstance(v, list) else v}" for k, v in detail.items()
        )
    elif isinstance(detail, list):
        message = "; ".join(str(d) for d in detail)
    else:
        message = str(detail)

    response.data = {
        "status": "error",
        "code": response.status_code,
        "error_code": error_code_map.get(response.status_code, "error"),
        "message": message,
    }
    return response
