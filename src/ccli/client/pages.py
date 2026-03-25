from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from ..auth import API_V1
from .base import ConfluenceClient

_SEARCH_PATH = f"{API_V1}/search"
_CONTENT_PATH = f"{API_V1}/content"

_GET_EXPAND = "body.view,body.storage,space,version,ancestors,history"


# --------------------------------------------------------------------------- #
# Public domain models                                                         #
# --------------------------------------------------------------------------- #


class Author(BaseModel):
    display_name: str
    email: Optional[str] = None


class Page(BaseModel):
    id: str
    title: str
    space_key: str
    space_name: str
    version: int
    created_at: str
    updated_at: str
    author: Author
    body_html: str
    body_storage: str  # Confluence Storage Format (XHTML-like)
    url: str
    parent_id: Optional[str] = None
    attachments: list[Any] = []  # populated in Phase 5


class PageSummary(BaseModel):
    id: str
    space_key: str
    space_name: str
    title: str
    url: str
    last_modified: str
    excerpt: str = ""


# --------------------------------------------------------------------------- #
# Internal Pydantic models for v1 API responses                                #
# --------------------------------------------------------------------------- #


class _SpaceInfo(BaseModel):
    key: str = ""
    name: str = ""


class _By(BaseModel):
    display_name: str = Field("", alias="displayName")
    email: Optional[str] = None

    model_config = {"populate_by_name": True}


class _Version(BaseModel):
    number: int
    when: str
    by: _By


class _History(BaseModel):
    created_date: str = Field("", alias="createdDate")
    created_by: _By = Field(default_factory=_By, alias="createdBy")

    model_config = {"populate_by_name": True}


class _BodyValue(BaseModel):
    value: str = ""


class _Body(BaseModel):
    view: _BodyValue = Field(default_factory=_BodyValue)
    storage: _BodyValue = Field(default_factory=_BodyValue)


class _Ancestor(BaseModel):
    id: str


class _ContentResponse(BaseModel):
    id: str
    title: str
    space: _SpaceInfo = Field(default_factory=_SpaceInfo)
    version: _Version
    history: _History = Field(default_factory=_History)
    body: _Body = Field(default_factory=_Body)
    ancestors: list[_Ancestor] = []
    links: dict[str, Any] = Field(default_factory=dict, alias="_links")

    model_config = {"populate_by_name": True}


class _SearchContent(BaseModel):
    id: str = ""
    space: _SpaceInfo = Field(default_factory=_SpaceInfo)
    links: dict[str, Any] = Field(default_factory=dict, alias="_links")

    model_config = {"populate_by_name": True}


class _SearchResult(BaseModel):
    content: Optional[_SearchContent] = None
    title: str = ""
    excerpt: str = ""
    url: str = ""
    last_modified: str = Field("", alias="lastModified")

    model_config = {"populate_by_name": True}


class _SearchResponse(BaseModel):
    results: list[_SearchResult]
    total_size: int = Field(0, alias="totalSize")

    model_config = {"populate_by_name": True}


# --------------------------------------------------------------------------- #
# Client                                                                       #
# --------------------------------------------------------------------------- #


class PagesClient:
    def __init__(self, client: ConfluenceClient, confluence_url: str) -> None:
        self._client = client
        self._base_url = confluence_url.rstrip("/")

    def search(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 25,
    ) -> list[PageSummary]:
        cql = f'text ~ "{query}" AND type = page'
        if space_key:
            cql += f' AND space = "{space_key}"'

        params: dict[str, Any] = {
            "cql": cql,
            "limit": limit,
            "expand": "content.space",
        }

        data = self._client.get(_SEARCH_PATH, params=params)
        response = _SearchResponse(**data)

        summaries: list[PageSummary] = []
        for result in response.results[:limit]:
            content = result.content
            summaries.append(
                PageSummary(
                    id=content.id if content else "",
                    space_key=content.space.key if content else "",
                    space_name=content.space.name if content else "",
                    title=result.title,
                    url=result.url or (
                        self._base_url + content.links.get("webui", "") if content else ""
                    ),
                    last_modified=result.last_modified,
                    excerpt=result.excerpt,
                )
            )

        return summaries

    def get(self, page_id: str) -> Page:
        params: dict[str, Any] = {"expand": _GET_EXPAND}
        data = self._client.get(f"{_CONTENT_PATH}/{page_id}", params=params)

        resp = _ContentResponse(**data)
        webui = resp.links.get("webui", "")
        parent_id = resp.ancestors[-1].id if resp.ancestors else None

        return Page(
            id=resp.id,
            title=resp.title,
            space_key=resp.space.key,
            space_name=resp.space.name,
            version=resp.version.number,
            created_at=resp.history.created_date,
            updated_at=resp.version.when,
            author=Author(
                display_name=resp.version.by.display_name,
                email=resp.version.by.email,
            ),
            body_html=resp.body.view.value,
            body_storage=resp.body.storage.value,
            url=f"{self._base_url}{webui}" if webui else "",
            parent_id=parent_id,
        )
