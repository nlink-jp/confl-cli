import json

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from ccli.main import app

runner = CliRunner()

BASE_URL = "https://example.atlassian.net"

ENV = {
    "CONFLUENCE_URL": BASE_URL,
    "CONFLUENCE_USERNAME": "user@example.com",
    "CONFLUENCE_API_TOKEN": "token123",
}

_SEARCH_RESPONSE = {
    "results": [
        {
            "content": {
                "id": "123",
                "space": {"key": "DEV", "name": "Development"},
                "_links": {"webui": "/spaces/DEV/pages/123"},
            },
            "title": "Getting Started",
            "excerpt": "intro content",
            "url": f"{BASE_URL}/wiki/spaces/DEV/pages/123",
            "lastModified": "2024-01-15T10:00:00.000Z",
        }
    ],
    "totalSize": 1,
}

_CONTENT_RESPONSE = {
    "id": "123",
    "title": "Getting Started",
    "space": {"key": "DEV", "name": "Development"},
    "version": {
        "number": 2,
        "when": "2024-01-15T10:00:00.000Z",
        "by": {"displayName": "John Doe"},
    },
    "history": {
        "createdDate": "2023-01-01T00:00:00.000Z",
        "createdBy": {"displayName": "Jane Smith"},
    },
    "body": {
        "view": {"value": "<p>Hello <strong>world</strong></p>"},
        "storage": {"value": "<p>Hello <ac:structured-macro ac:name=\"strong\" /></p>"},
    },
    "ancestors": [],
    "_links": {"webui": "/wiki/spaces/DEV/pages/123"},
}


@pytest.fixture(autouse=True)
def set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)


class TestPagesSearch:
    def test_text_output(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_SEARCH_RESPONSE)
        result = runner.invoke(app, ["pages", "search", "getting started"])
        assert result.exit_code == 0
        assert "Getting Started" in result.output
        assert "DEV" in result.output

    def test_json_output(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_SEARCH_RESPONSE)
        result = runner.invoke(app, ["pages", "search", "getting started", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["id"] == "123"
        assert data[0]["title"] == "Getting Started"

    def test_date_truncated_to_date(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_SEARCH_RESPONSE)
        result = runner.invoke(app, ["pages", "search", "x"])
        assert "2024-01-15" in result.output
        assert "T10:00:00" not in result.output

    def test_empty_results(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [], "totalSize": 0})
        result = runner.invoke(app, ["pages", "search", "nothing"])
        assert result.exit_code == 0
        assert "No pages found" in result.output

    def test_space_filter_passed(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_SEARCH_RESPONSE)
        runner.invoke(app, ["pages", "search", "x", "--space", "DEV"])
        request = httpx_mock.get_requests()[0]
        assert "DEV" in str(request.url)

    def test_auth_error_exits_1(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401)
        result = runner.invoke(app, ["pages", "search", "x"])
        assert result.exit_code == 1


class TestPagesGet:
    def test_text_output(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        result = runner.invoke(app, ["pages", "get", "123"])
        assert result.exit_code == 0
        assert "Getting Started" in result.output
        assert "Hello" in result.output

    def test_html_output(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        result = runner.invoke(app, ["pages", "get", "123", "--format", "html"])
        assert result.exit_code == 0
        assert "<p>" in result.output

    def test_json_output(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        result = runner.invoke(app, ["pages", "get", "123", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "123"
        assert data["title"] == "Getting Started"
        assert "body_html" in data

    def test_storage_output(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_CONTENT_RESPONSE)
        result = runner.invoke(app, ["pages", "get", "123", "--format", "storage"])
        assert result.exit_code == 0
        assert "ac:structured-macro" in result.output

    def test_not_found_exits_3(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404)
        result = runner.invoke(app, ["pages", "get", "999"])
        assert result.exit_code == 3
