import pytest
from pytest_httpx import HTTPXMock

from ccli.auth import build_client
from ccli.client.base import ConfluenceClient
from ccli.client.pages import PagesClient
from ccli.config import Config, ConfluenceSettings
from ccli.exceptions import NotFoundError

BASE_URL = "https://example.atlassian.net"

_SEARCH_RESPONSE = {
    "results": [
        {
            "content": {
                "id": "123",
                "space": {"key": "DEV", "name": "Development"},
                "_links": {"webui": "/spaces/DEV/pages/123/My+Page"},
            },
            "title": "My Page",
            "excerpt": "Some <b>content</b> here",
            "url": "https://example.atlassian.net/wiki/spaces/DEV/pages/123",
            "lastModified": "2024-01-15T10:00:00.000Z",
        }
    ],
    "totalSize": 1,
}

_CONTENT_RESPONSE = {
    "id": "123",
    "title": "My Page",
    "space": {"key": "DEV", "name": "Development"},
    "version": {
        "number": 3,
        "when": "2024-01-15T10:00:00.000Z",
        "by": {"displayName": "John Doe", "email": "john@example.com"},
    },
    "history": {
        "createdDate": "2023-06-01T08:00:00.000Z",
        "createdBy": {"displayName": "Jane Smith"},
    },
    "body": {
        "view": {"value": "<p>Hello <strong>world</strong></p>"},
        "storage": {
            "value": (
                "<p>Hello <ac:structured-macro ac:name=\"strong\">"
                "<ac:rich-text-body>world</ac:rich-text-body>"
                "</ac:structured-macro></p>"
            )
        },
    },
    "ancestors": [{"id": "100"}, {"id": "101"}],
    "_links": {"webui": "/wiki/spaces/DEV/pages/123/My+Page"},
}


def _make_client(httpx_mock: HTTPXMock) -> PagesClient:
    config = Config(
        confluence=ConfluenceSettings(url=BASE_URL, username="u@example.com", api_token="tok")
    )
    return PagesClient(ConfluenceClient(build_client(config)), BASE_URL)


class TestPagesSearch:
    def test_returns_summaries(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_SEARCH_RESPONSE)
        client = _make_client(httpx_mock)
        results = client.search("my page")
        assert len(results) == 1
        assert results[0].id == "123"
        assert results[0].space_key == "DEV"
        assert results[0].title == "My Page"

    def test_sends_cql_query(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_SEARCH_RESPONSE)
        client = _make_client(httpx_mock)
        client.search("my page")
        request = httpx_mock.get_requests()[0]
        assert "cql=" in str(request.url)
        assert "type+%3D+page" in str(request.url) or "type = page" in str(request.url)

    def test_filters_by_space(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_SEARCH_RESPONSE)
        client = _make_client(httpx_mock)
        client.search("my page", space_key="DEV")
        request = httpx_mock.get_requests()[0]
        assert "DEV" in str(request.url)

    def test_last_modified_propagated(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_SEARCH_RESPONSE)
        client = _make_client(httpx_mock)
        results = client.search("my page")
        assert results[0].last_modified == "2024-01-15T10:00:00.000Z"

    def test_empty_results(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [], "totalSize": 0})
        client = _make_client(httpx_mock)
        assert client.search("nothing") == []


class TestPagesGet:
    def test_returns_page(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        client = _make_client(httpx_mock)
        page = client.get("123")
        assert page.id == "123"
        assert page.title == "My Page"
        assert page.space_key == "DEV"
        assert page.version == 3

    def test_dates_populated(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        client = _make_client(httpx_mock)
        page = client.get("123")
        assert page.created_at == "2023-06-01T08:00:00.000Z"
        assert page.updated_at == "2024-01-15T10:00:00.000Z"

    def test_author_populated(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        client = _make_client(httpx_mock)
        page = client.get("123")
        assert page.author.display_name == "John Doe"
        assert page.author.email == "john@example.com"

    def test_body_html_populated(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        client = _make_client(httpx_mock)
        page = client.get("123")
        assert "<p>" in page.body_html

    def test_body_storage_populated(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        client = _make_client(httpx_mock)
        page = client.get("123")
        assert "ac:structured-macro" in page.body_storage

    def test_parent_id_is_last_ancestor(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        client = _make_client(httpx_mock)
        page = client.get("123")
        assert page.parent_id == "101"  # last ancestor

    def test_no_ancestors_gives_none_parent(self, httpx_mock: HTTPXMock) -> None:
        response = {**_CONTENT_RESPONSE, "ancestors": []}
        httpx_mock.add_response(json=response)
        client = _make_client(httpx_mock)
        page = client.get("123")
        assert page.parent_id is None

    def test_404_raises_not_found(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404)
        client = _make_client(httpx_mock)
        with pytest.raises(NotFoundError):
            client.get("999")

    def test_url_constructed_from_webui(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        client = _make_client(httpx_mock)
        page = client.get("123")
        assert page.url.startswith(BASE_URL)
