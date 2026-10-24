"""Small polite JSON client (stdlib only): identifying User-Agent, rate limit, retries, cache."""

import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "EasyMealsHarvester/0.1 (open-data import; contact: project maintainer)"


class JsonClient:
    def __init__(
        self,
        delay: float = 0.5,
        retries: int = 3,
        timeout: float = 20.0,
        cache_dir: Path | None = None,
    ) -> None:
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._last_call = 0.0

    def get_json(self, url: str) -> dict:
        cached = self._cache_path(url)
        if cached and cached.exists():
            return json.loads(cached.read_text(encoding="utf-8"))

        data: dict = {}
        for attempt in range(1, self.retries + 1):
            self._wait()
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                client_error = isinstance(exc, urllib.error.HTTPError) and exc.code < 500
                if attempt == self.retries or client_error:
                    raise RuntimeError(f"GET {url} failed: {exc}") from exc
                time.sleep(2**attempt)

        if cached:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data

    def _wait(self) -> None:
        remaining = self.delay - (time.monotonic() - self._last_call)
        if remaining > 0:
            time.sleep(remaining)
        self._last_call = time.monotonic()

    def _cache_path(self, url: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")
