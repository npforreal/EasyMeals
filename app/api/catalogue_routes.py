"""Endpoint for syncing public catalogue with client IndexedDB."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_repo
from app.storage.repository import Repository

router = APIRouter(prefix="/api/catalogue", tags=["Catalogue"])


@router.get("")
def get_catalogue(
    request: Request,
    repo: Repository = Depends(get_repo),
) -> Response:
    """Fetch complete catalogue bundle with ETag support for offline IndexedDB sync."""
    bundle = repo.get_catalogue_bundle()
    etag = bundle.get("etag", "")

    # Check client's If-None-Match header
    client_etag = request.headers.get("if-none-match")
    if client_etag and client_etag == etag:
        return Response(status_code=304)

    return JSONResponse(
        content=bundle,
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
        },
    )
