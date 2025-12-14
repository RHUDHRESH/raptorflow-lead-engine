"""
Custom error handlers for consistent, human-readable error responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register all custom error handlers with the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors with user-friendly field details."""
        errors = exc.errors()

        # Extract field-level errors
        field_errors = {}
        for error in errors:
            loc = error.get("loc", [])
            msg = error.get("msg", "Unknown error")
            # Build field name from location tuple
            field_name = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else "unknown"
            field_errors[field_name] = msg

        logger.warning(f"Validation error on {request.url}: {field_errors}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload",
                "details": field_errors,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions (HTTPException from FastAPI)."""
        logger.warning(f"HTTP {exc.status_code} on {request.url}: {exc.detail}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "code": f"HTTP_{exc.status_code}",
                "message": "Request error",
                "detail": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions safely without exposing internals."""
        logger.error(
            f"Unhandled {type(exc).__name__} on {request.url}: {exc}",
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "detail": "An unexpected error occurred. Please try again later.",
            },
        )
