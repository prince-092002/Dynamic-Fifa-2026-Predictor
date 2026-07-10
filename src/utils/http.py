"""HTTP helpers with polite defaults and retry behavior."""

from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    requests = None


DEFAULT_HEADERS = {
    "User-Agent": (
        "DynamicFIFA2026Predictor/0.1 "
        "(educational data project; polite contact: local-user)"
    )
}


class HTTPFetchError(RuntimeError):
    """Raised when a remote request cannot be completed safely."""


try:
    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

    retry_exceptions = (HTTPFetchError,)
    if requests is not None:
        retry_exceptions = (requests.RequestException, HTTPFetchError)

    retry_http = retry(
        retry=retry_if_exception_type(retry_exceptions),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
except ImportError:
    def retry_http(function):
        return function


@retry_http
def get_text(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    params: Optional[Dict[str, Any]] = None,
) -> str:
    if requests is None:
        raise HTTPFetchError("Install project requirements first: pip install -r requirements.txt")
    response = requests.get(
        url,
        headers={**DEFAULT_HEADERS, **(headers or {})},
        params=params,
        timeout=timeout,
    )
    if response.status_code == 429:
        raise HTTPFetchError("Rate limited by remote source")
    response.raise_for_status()
    return response.text


def get_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if requests is None:
        raise HTTPFetchError("Install project requirements first: pip install -r requirements.txt")
    response = requests.get(
        url,
        headers={**DEFAULT_HEADERS, **(headers or {})},
        params=params,
        timeout=timeout,
    )
    if response.status_code == 429:
        raise HTTPFetchError("Rate limited by remote source")
    response.raise_for_status()
    return response.json()
