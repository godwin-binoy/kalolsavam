"""Unified error handling: no stack traces leak to clients."""
from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("kalolsavam")


async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "")
    if exc.status_code >= 500:
        log.error(
            "http_5xx",
            extra={
                "request_id": req_id,
                "method": request.method,
                "path": request.url.path,
                "status": exc.status_code,
            },
        )
        return JSONResponse(
            {"error": "internal", "request_id": req_id},
            status_code=500,
        )
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(detail, status_code=exc.status_code)
    return JSONResponse({"error": str(detail)}, status_code=exc.status_code)
