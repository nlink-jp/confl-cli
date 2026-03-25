from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, Field

from ..auth import API_V2
from .base import ConfluenceClient


class Attachment(BaseModel):
    id: str
    filename: str
    media_type: str
    size_bytes: int
    download_url: str  # relative URL (e.g. /wiki/download/attachments/...)
    saved_path: str | None = None  # populated after download


class _AttachmentMeta(BaseModel):
    id: str
    title: str
    media_type: str = Field("application/octet-stream", alias="mediaType")
    file_size: int = Field(0, alias="fileSize")
    # v2 may return download URL either at top-level or inside _links
    download_link: str = Field("", alias="downloadLink")
    links: dict[str, Any] = Field(default_factory=dict, alias="_links")

    model_config = {"populate_by_name": True}

    @property
    def resolved_download_url(self) -> str:
        return self.download_link or self.links.get("download", "")


class _AttachmentsResponse(BaseModel):
    results: list[_AttachmentMeta]
    links: dict[str, Any] = Field(default_factory=dict, alias="_links")

    model_config = {"populate_by_name": True}


def _normalize_download_url(url: str) -> str:
    """Prepend /wiki if the URL is a Confluence-relative path lacking it.

    The v2 API _links.download sometimes returns /download/... instead of
    /wiki/download/..., depending on the instance version.
    """
    if url and not url.startswith("/wiki") and not url.startswith("http"):
        return "/wiki" + url
    return url


class AttachmentsClient:
    def __init__(self, client: ConfluenceClient) -> None:
        self._client = client

    def list(self, page_id: str) -> list[Attachment]:
        """Return all attachments for *page_id*, following pagination cursors."""
        attachments: list[Attachment] = []
        cursor: str | None = None

        while True:
            params: dict[str, Any] = {"limit": 250}
            if cursor:
                params["cursor"] = cursor

            data = self._client.get(f"{API_V2}/pages/{page_id}/attachments", params=params)
            resp = _AttachmentsResponse(**data)

            for meta in resp.results:
                attachments.append(
                    Attachment(
                        id=meta.id,
                        filename=meta.title,
                        media_type=meta.media_type,
                        size_bytes=meta.file_size,
                        download_url=_normalize_download_url(meta.resolved_download_url),
                    )
                )

            next_url = resp.links.get("next")
            if not next_url:
                break
            qs = parse_qs(urlparse(next_url).query)
            cursors = qs.get("cursor", [])
            cursor = cursors[0] if cursors else None
            if not cursor:
                break

        return attachments
