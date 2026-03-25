import json

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from ccli.main import app

runner = CliRunner()

BASE_URL = "https://example.atlassian.net"
SPACES_URL = f"{BASE_URL}/wiki/api/v2/spaces"

_SPACE_A = {"id": "1", "key": "DEV", "name": "Development", "type": "global", "status": "current"}
_SPACE_B = {"id": "2", "key": "ARCH", "name": "Architecture", "type": "global", "status": "current"}

ENV = {
    "CONFLUENCE_URL": BASE_URL,
    "CONFLUENCE_USERNAME": "user@example.com",
    "CONFLUENCE_API_TOKEN": "token123",
}


@pytest.fixture(autouse=True)
def set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)


class TestSpacesList:
    def test_text_output(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [_SPACE_A, _SPACE_B], "_links": {}})
        result = runner.invoke(app, ["spaces", "list"])
        assert result.exit_code == 0
        assert "DEV" in result.output
        assert "ARCH" in result.output
        assert "Development" in result.output

    def test_json_output(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [_SPACE_A], "_links": {}})
        result = runner.invoke(app, ["spaces", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["key"] == "DEV"

    def test_empty_list(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [], "_links": {}})
        result = runner.invoke(app, ["spaces", "list"])
        assert result.exit_code == 0
        assert "No spaces found" in result.output

    def test_auth_error_exits_1(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401)
        result = runner.invoke(app, ["spaces", "list"])
        assert result.exit_code == 1

    def test_limit_option(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [_SPACE_A, _SPACE_B], "_links": {}})
        result = runner.invoke(app, ["spaces", "list", "--limit", "1"])
        assert result.exit_code == 0
        data_lines = [
            line for line in result.output.splitlines() if "DEV" in line or "ARCH" in line
        ]
        assert len(data_lines) == 1


class TestSpacesSearch:
    def test_returns_matching_spaces(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [_SPACE_A, _SPACE_B], "_links": {}})
        result = runner.invoke(app, ["spaces", "search", "arch"])
        assert result.exit_code == 0
        assert "ARCH" in result.output
        assert "DEV" not in result.output

    def test_json_output(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [_SPACE_A, _SPACE_B], "_links": {}})
        result = runner.invoke(app, ["spaces", "search", "dev", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["key"] == "DEV"

    def test_no_match_shows_empty(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [_SPACE_A], "_links": {}})
        result = runner.invoke(app, ["spaces", "search", "zzz"])
        assert result.exit_code == 0
        assert "No spaces found" in result.output
