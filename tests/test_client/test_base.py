import httpx
import pytest
from pytest_httpx import HTTPXMock

from ccli.auth import build_client
from ccli.client.base import ConfluenceClient
from ccli.config import Config, ConfluenceSettings
from ccli.exceptions import AuthError, ForbiddenError, NetworkError, NotFoundError, RateLimitError

BASE_URL = "https://example.atlassian.net"


def _make_client(httpx_mock: HTTPXMock) -> ConfluenceClient:
    config = Config(
        confluence=ConfluenceSettings(url=BASE_URL, username="u@example.com", api_token="tok")
    )
    return ConfluenceClient(build_client(config))


class TestGetSuccess:
    def test_returns_parsed_json(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [], "_links": {}})
        client = _make_client(httpx_mock)
        data = client.get("/wiki/api/v2/spaces")
        assert data == {"results": [], "_links": {}}

    def test_passes_query_params(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={})
        client = _make_client(httpx_mock)
        client.get("/wiki/api/v2/spaces", params={"limit": 10, "type": "global"})
        request = httpx_mock.get_requests()[0]
        assert "limit=10" in str(request.url)
        assert "type=global" in str(request.url)


class TestErrorMapping:
    def test_401_raises_auth_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401)
        client = _make_client(httpx_mock)
        with pytest.raises(AuthError):
            client.get("/wiki/api/v2/spaces")

    def test_403_raises_forbidden_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403)
        client = _make_client(httpx_mock)
        with pytest.raises(ForbiddenError):
            client.get("/wiki/api/v2/spaces")

    def test_404_raises_not_found_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404)
        client = _make_client(httpx_mock)
        with pytest.raises(NotFoundError):
            client.get("/wiki/api/v2/spaces")


class TestRateLimitRetry:
    def test_retries_on_429_and_succeeds(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("ccli.client.base.time.sleep", lambda _: None)
        httpx_mock.add_response(status_code=429)
        httpx_mock.add_response(json={"ok": True})
        client = _make_client(httpx_mock)
        data = client.get("/wiki/api/v2/spaces")
        assert data == {"ok": True}

    def test_raises_after_max_retries(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("ccli.client.base.time.sleep", lambda _: None)
        for _ in range(4):  # _MAX_RETRIES + 1
            httpx_mock.add_response(status_code=429)
        client = _make_client(httpx_mock)
        with pytest.raises(RateLimitError):
            client.get("/wiki/api/v2/spaces")

    def test_respects_retry_after_header(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sleep_calls: list[float] = []
        monkeypatch.setattr("ccli.client.base.time.sleep", lambda s: sleep_calls.append(s))
        httpx_mock.add_response(status_code=429, headers={"Retry-After": "5"})
        httpx_mock.add_response(json={})
        client = _make_client(httpx_mock)
        client.get("/wiki/api/v2/spaces")
        assert sleep_calls[0] == 5.0


class TestNetworkErrorRetry:
    def test_retries_on_network_error_and_succeeds(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("ccli.client.base.time.sleep", lambda _: None)
        httpx_mock.add_exception(httpx.NetworkError("connection refused"))
        httpx_mock.add_response(json={"ok": True})
        client = _make_client(httpx_mock)
        data = client.get("/wiki/api/v2/spaces")
        assert data == {"ok": True}

    def test_raises_network_error_after_max_retries(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("ccli.client.base.time.sleep", lambda _: None)
        for _ in range(4):  # _MAX_RETRIES + 1
            httpx_mock.add_exception(httpx.NetworkError("connection refused"))
        client = _make_client(httpx_mock)
        with pytest.raises(NetworkError):
            client.get("/wiki/api/v2/spaces")

    def test_backoff_applied_on_network_error(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sleep_calls: list[float] = []
        monkeypatch.setattr("ccli.client.base.time.sleep", lambda s: sleep_calls.append(s))
        httpx_mock.add_exception(httpx.NetworkError("connection refused"))
        httpx_mock.add_response(json={})
        client = _make_client(httpx_mock)
        client.get("/wiki/api/v2/spaces")
        assert sleep_calls[0] == 1.0  # _RETRY_BASE_DELAY * 2**0


class TestServerErrorRetry:
    def test_retries_on_500_and_succeeds(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("ccli.client.base.time.sleep", lambda _: None)
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(json={"ok": True})
        client = _make_client(httpx_mock)
        data = client.get("/wiki/api/v2/spaces")
        assert data == {"ok": True}

    def test_raises_network_error_after_max_500_retries(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("ccli.client.base.time.sleep", lambda _: None)
        for _ in range(4):  # _MAX_RETRIES + 1
            httpx_mock.add_response(status_code=500)
        client = _make_client(httpx_mock)
        with pytest.raises(NetworkError):
            client.get("/wiki/api/v2/spaces")

    def test_backoff_applied_on_500(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sleep_calls: list[float] = []
        monkeypatch.setattr("ccli.client.base.time.sleep", lambda s: sleep_calls.append(s))
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(json={})
        client = _make_client(httpx_mock)
        client.get("/wiki/api/v2/spaces")
        assert sleep_calls[0] == 1.0  # _RETRY_BASE_DELAY * 2**0
