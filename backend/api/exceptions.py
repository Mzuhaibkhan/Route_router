"""
Custom exception handler for Spotter AI DRF endpoints.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Standardize API error responses with a consistent payload format.
    """
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "error": True,
            "status_code": response.status_code,
            "details": response.data,
        }
        return response

    return Response(
        {
            "error": True,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "details": "An unexpected server error occurred.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
