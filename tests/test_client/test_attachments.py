from pytest_httpx import HTTPXMock

from ccli.auth import build_client
from ccli.client.attachments import AttachmentsClient
from ccli.client.base import ConfluenceClient
from ccli.config import Config, ConfluenceSettings

BASE_URL = "https://example.atlassian.net"

_ATT_A = {
    "id": "att001",
    "title": "design.pdf",
    "mediaType": "application/pdf",
    "fileSize": 102400,
    "_links": {"download": "/wiki/download/attachments/100/design.pdf"},
}
_ATT_B = {
    "id": "att002",
    "title": "photo.png",
    "mediaType": "image/png",
    "fileSize": 51200,
    "_links": {"download": "/wiki/download/attachments/100/photo.png"},
}


def _make_client(httpx_mock: HTTPXMock) -> AttachmentsClient:
    config = Config(
        confluence=ConfluenceSettings(url=BASE_URL, username="u@example.com", api_token="tok")
    )
    return AttachmentsClient(ConfluenceClient(build_client(config)))


class TestAttachmentsList:
    def test_returns_attachments(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [_ATT_A, _ATT_B], "_links": {}})
        client = _make_client(httpx_mock)
        attachments = client.list("100")
        assert len(attachments) == 2
        assert attachments[0].id == "att001"
        assert attachments[0].filename == "design.pdf"
        assert attachments[0].media_type == "application/pdf"
        assert attachments[0].size_bytes == 102400

    def test_download_url_from_links(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [_ATT_A], "_links": {}})
        client = _make_client(httpx_mock)
        attachments = client.list("100")
        assert attachments[0].download_url == "/wiki/download/attachments/100/design.pdf"

    def test_download_url_from_top_level_field(self, httpx_mock: HTTPXMock) -> None:
        # downloadLink without /wiki prefix → should be normalized to /wiki/...
        att = {**_ATT_A, "downloadLink": "/direct/download/link", "_links": {}}
        httpx_mock.add_response(json={"results": [att], "_links": {}})
        client = _make_client(httpx_mock)
        attachments = client.list("100")
        assert attachments[0].download_url == "/wiki/direct/download/link"

    def test_empty_results(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [], "_links": {}})
        client = _make_client(httpx_mock)
        assert client.list("100") == []

    def test_saved_path_is_none_by_default(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json={"results": [_ATT_A], "_links": {}})
        client = _make_client(httpx_mock)
        attachments = client.list("100")
        assert attachments[0].saved_path is None

    def test_pagination(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json={
                "results": [_ATT_A],
                "_links": {
                    "next": f"{BASE_URL}/wiki/api/v2/pages/100/attachments?cursor=xyz"
                },
            }
        )
        httpx_mock.add_response(json={"results": [_ATT_B], "_links": {}})
        client = _make_client(httpx_mock)
        attachments = client.list("100")
        assert len(attachments) == 2
