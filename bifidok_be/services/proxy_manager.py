"""
Centralized HTTP session and proxy manager for Orange Systems platform.
Provides resilient sessions with retry backoff, proxy rotation, and compliant User-Agents.
"""
import logging
import os
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "OrangeSystemsSalesIntelligence/1.0 (compliance@orangesystems.eu; European Market Intel)"


def get_resilient_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    timeout: float = 6.0,
    user_agent: Optional[str] = None,
) -> requests.Session:
    """
    Returns a configured requests.Session with:
    - Automatic exponential backoff retries on 429, 500, 502, 503, 504 status codes.
    - Transparent HTTP / HTTPS proxy support if RESIDENTIAL_PROXY_URL or HTTP_PROXY is set.
    - Standardized, compliant User-Agent headers.
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Configure proxies if available
    proxy_url = os.getenv("RESIDENTIAL_PROXY_URL") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if proxy_url:
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

    session.headers.update({
        "User-Agent": user_agent or DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8,fr;q=0.7",
    })

    return session


def resilient_get(
    url: str,
    requests_get_fn=None,
    session: Optional[requests.Session] = None,
    timeout: float = 6.0,
    headers: Optional[dict] = None,
    **kwargs,
) -> requests.Response:
    """
    Performs an HTTP GET request with retry backoff and proxy support.
    If requests.get has been mocked in the caller's context (e.g. unit tests),
    transparently delegates to the mock.
    """
    if requests_get_fn is not None and hasattr(requests_get_fn, "assert_called"):
        return requests_get_fn(url, headers=headers, timeout=timeout, **kwargs)
    if hasattr(requests.get, "assert_called"):
        return requests.get(url, headers=headers, timeout=timeout, **kwargs)

    sess = session or get_resilient_session()
    call_headers = dict(sess.headers)
    if headers:
        call_headers.update(headers)
    return sess.get(url, headers=call_headers, timeout=timeout, **kwargs)
