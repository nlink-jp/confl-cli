import time
from typing import Any

import httpx

from ..exceptions import AuthError, ForbiddenError, NetworkError, NotFoundError, RateLimitError

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0


class ConfluenceClient:
    """Thin wrapper around httpx.Client that maps HTTP errors to domain exceptions
    and retries on transient failures with exponential back-off.

    Retried conditions:
    - 429 Too Many Requests  (honours Retry-After header)
    - 5xx Server Error       (exponential back-off)
    - httpx.NetworkError     (exponential back-off)
    - httpx.TimeoutException (exponential back-off)

    Non-retried conditions (fail immediately):
    - 401 → AuthError
    - 403 → ForbiddenError
    - 404 → NotFoundError
    - other 4xx → httpx.HTTPStatusError
    """

    def __init__(self, http_client: httpx.Client) -> None:
        self._http = http_client

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 401:
            raise AuthError()
        if response.status_code == 403:
            raise ForbiddenError()
        if response.status_code == 404:
            raise NotFoundError()
        response.raise_for_status()

    @staticmethod
    def _backoff(attempt: int, response: httpx.Response | None = None) -> float:
        """Return seconds to wait before the next attempt."""
        delay: float = _RETRY_BASE_DELAY * (2**attempt)
        if response is not None and response.status_code == 429:
            raw = response.headers.get("Retry-After")  # Any in httpx stubs
            if raw is not None:
                try:
                    delay = float(raw)
                except ValueError:
                    pass
        return delay

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = self._http.get(path, params=params)
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                if attempt < _MAX_RETRIES:
                    time.sleep(self._backoff(attempt))
                    continue
                raise NetworkError(str(exc)) from exc

            if response.status_code == 429:
                if attempt < _MAX_RETRIES:
                    time.sleep(self._backoff(attempt, response))
                    continue
                raise RateLimitError()

            if response.status_code >= 500:
                if attempt < _MAX_RETRIES:
                    time.sleep(self._backoff(attempt))
                    continue
                raise NetworkError(f"Server error {response.status_code} from Confluence")

            self._raise_for_status(response)
            result: dict[str, Any] = response.json()
            return result

        raise NetworkError("Max retries exceeded")  # pragma: no cover
