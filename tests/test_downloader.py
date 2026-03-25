from pathlib import Path

import httpx
import pytest
from pytest_httpx import HTTPXMock

from ccli.auth import build_client
from ccli.config import Config, ConfluenceSettings
from ccli.downloader import download_file, safe_attachment_dest

BASE_URL = "https://example.atlassian.net"
DOWNLOAD_URL = "/wiki/download/attachments/100/file.pdf"


def _make_http_client() -> object:
    config = Config(
        confluence=ConfluenceSettings(url=BASE_URL, username="u@example.com", api_token="tok")
    )
    return build_client(config)


def test_downloads_file_to_dest(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    content = b"PDF file content here"
    httpx_mock.add_response(url=f"{BASE_URL}{DOWNLOAD_URL}", content=content)
    http_client = _make_http_client()
    dest = tmp_path / "downloads" / "file.pdf"

    download_file(http_client, DOWNLOAD_URL, dest)

    assert dest.exists()
    assert dest.read_bytes() == content


def test_creates_parent_directories(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    httpx_mock.add_response(content=b"data")
    http_client = _make_http_client()
    dest = tmp_path / "a" / "b" / "c" / "file.bin"

    download_file(http_client, DOWNLOAD_URL, dest)

    assert dest.parent.exists()


def test_overwrites_existing_file(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    dest = tmp_path / "file.txt"
    dest.write_bytes(b"old content")

    httpx_mock.add_response(content=b"new content")
    download_file(_make_http_client(), DOWNLOAD_URL, dest)

    assert dest.read_bytes() == b"new content"


# --------------------------------------------------------------------------- #
# download_file retry                                                           #
# --------------------------------------------------------------------------- #


class TestDownloadFileRetry:
    def test_retries_on_network_error_and_succeeds(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr("ccli.downloader.time.sleep", lambda _: None)
        httpx_mock.add_exception(httpx.NetworkError("connection reset"))
        httpx_mock.add_response(content=b"good data")
        dest = tmp_path / "file.bin"
        download_file(_make_http_client(), DOWNLOAD_URL, dest)
        assert dest.read_bytes() == b"good data"

    def test_retries_on_server_error_and_succeeds(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr("ccli.downloader.time.sleep", lambda _: None)
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(content=b"good data")
        dest = tmp_path / "file.bin"
        download_file(_make_http_client(), DOWNLOAD_URL, dest)
        assert dest.read_bytes() == b"good data"

    def test_removes_partial_file_before_retry(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr("ccli.downloader.time.sleep", lambda _: None)
        httpx_mock.add_exception(httpx.NetworkError("connection reset"))
        httpx_mock.add_response(content=b"good data")
        dest = tmp_path / "file.bin"
        dest.write_bytes(b"partial")  # simulate leftover from previous run
        download_file(_make_http_client(), DOWNLOAD_URL, dest)
        assert dest.read_bytes() == b"good data"

    def test_raises_after_max_retries_on_network_error(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr("ccli.downloader.time.sleep", lambda _: None)
        for _ in range(4):  # _MAX_RETRIES + 1
            httpx_mock.add_exception(httpx.NetworkError("connection reset"))
        dest = tmp_path / "file.bin"
        with pytest.raises(httpx.NetworkError):
            download_file(_make_http_client(), DOWNLOAD_URL, dest)

    def test_raises_after_max_retries_on_server_error(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr("ccli.downloader.time.sleep", lambda _: None)
        for _ in range(4):  # _MAX_RETRIES + 1
            httpx_mock.add_response(status_code=500)
        dest = tmp_path / "file.bin"
        with pytest.raises(httpx.HTTPStatusError):
            download_file(_make_http_client(), DOWNLOAD_URL, dest)

    def test_does_not_retry_on_4xx(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr("ccli.downloader.time.sleep", lambda _: None)
        httpx_mock.add_response(status_code=404)
        dest = tmp_path / "file.bin"
        with pytest.raises(httpx.HTTPStatusError):
            download_file(_make_http_client(), DOWNLOAD_URL, dest)
        assert len(httpx_mock.get_requests()) == 1  # no retry

    def test_backoff_applied_on_network_error(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        sleep_calls: list[float] = []
        monkeypatch.setattr("ccli.downloader.time.sleep", lambda s: sleep_calls.append(s))
        httpx_mock.add_exception(httpx.NetworkError("connection reset"))
        httpx_mock.add_response(content=b"data")
        dest = tmp_path / "file.bin"
        download_file(_make_http_client(), DOWNLOAD_URL, dest)
        assert sleep_calls[0] == 1.0  # _RETRY_BASE_DELAY * 2**0


# --------------------------------------------------------------------------- #
# safe_attachment_dest                                                          #
# --------------------------------------------------------------------------- #


class TestSafeAttachmentDest:
    def test_normal_filename(self, tmp_path: Path) -> None:
        dest = safe_attachment_dest(tmp_path, "123", "report.pdf")
        assert dest == (tmp_path / "123" / "report.pdf").resolve()

    def test_absolute_path_in_filename(self, tmp_path: Path) -> None:
        # /etc/passwd → only the basename "passwd" should be used
        dest = safe_attachment_dest(tmp_path, "123", "/etc/passwd")
        assert dest.name == "passwd"
        assert dest.is_relative_to(tmp_path.resolve())

    def test_directory_traversal_in_filename(self, tmp_path: Path) -> None:
        # ../../.bashrc → only ".bashrc" should be used
        dest = safe_attachment_dest(tmp_path, "123", "../../.bashrc")
        assert dest.name == ".bashrc"
        assert dest.is_relative_to(tmp_path.resolve())

    def test_null_byte_in_filename(self, tmp_path: Path) -> None:
        dest = safe_attachment_dest(tmp_path, "123", "evil\x00.txt")
        assert "\x00" not in dest.name
        assert dest.is_relative_to(tmp_path.resolve())

    def test_degenerate_dotdot_filename(self, tmp_path: Path) -> None:
        dest = safe_attachment_dest(tmp_path, "123", "..")
        assert dest.name == "attachment"

    def test_empty_filename(self, tmp_path: Path) -> None:
        dest = safe_attachment_dest(tmp_path, "123", "")
        assert dest.name == "attachment"

    def test_path_separator_in_page_id(self, tmp_path: Path) -> None:
        dest = safe_attachment_dest(tmp_path, "../evil", "file.txt")
        assert dest.is_relative_to(tmp_path.resolve())

    def test_windows_backslash_in_filename(self, tmp_path: Path) -> None:
        # On non-Windows, backslash is a valid filename char but Path.name handles it
        dest = safe_attachment_dest(tmp_path, "123", "sub\\file.txt")
        assert dest.is_relative_to(tmp_path.resolve())
