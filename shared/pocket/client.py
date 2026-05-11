"""Async HeyPocket API client with retry logic and rate limiting."""

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from shared.errors import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)
from shared.pocket.config import HeyPocketConfig
from shared.pocket.models import (
    HeyPocketRecording,
    SummarizationData,
    TranscriptData,
)

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker to prevent hammering failing services."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self._lock = asyncio.Lock()

    async def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection.

        Returns:
            Result of the executed function.

        Raises:
            APIError: If circuit breaker is open.
        """
        async with self._lock:
            if self._is_open():
                msg = (
                    f"Circuit breaker open - too many failures. "
                    f"Try again after {self.recovery_timeout}s"
                )
                raise APIError(msg)

        try:
            result = await func(*args, **kwargs)
        except Exception:
            await self._record_failure()
            raise
        else:
            await self._reset()
            return result

    def _is_open(self) -> bool:
        """Check if circuit breaker is open.

        Returns:
            True if circuit is open, False otherwise.
        """
        if self.failure_count >= self.failure_threshold:
            if self.last_failure_time:
                age = (datetime.now() - self.last_failure_time).total_seconds()
                if age < self.recovery_timeout:
                    return True
            # Reset if recovery timeout passed
            self.failure_count = 0
        return False

    async def _record_failure(self) -> None:
        """Record a failure."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

    async def _reset(self) -> None:
        """Reset circuit breaker after success."""
        async with self._lock:
            self.failure_count = 0
            self.last_failure_time = None


class HeyPocketClient:
    """Async HeyPocket API client with retry logic and rate limiting."""

    def __init__(self, config: HeyPocketConfig):
        self.config = config
        self._session: aiohttp.ClientSession | None = None
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
        )
        self._timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self._session_lock = asyncio.Lock()

    async def __aenter__(self) -> "HeyPocketClient":
        """Enter async context, ensuring session exists.

        Returns:
            The HeyPocketClient instance.
        """
        await self._ensure_session()
        return self

    async def __aexit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Exit async context, closing the session."""
        await self.close()

    async def _ensure_session(self) -> None:
        async with self._session_lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(timeout=self._timeout)

    async def close(self) -> None:
        """Close the HTTP session if open."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_headers(self) -> dict[str, str]:
        """Get headers with authentication.

        Returns:
            Dictionary of HTTP headers including authorization.
        """
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10, jitter=3),
        retry=retry_if_exception_type((aiohttp.ClientError, APIError)),
        reraise=True,
    )
    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        """Make HTTP request with retry, circuit breaker, and timeout.

        Returns:
            JSON response as a dictionary.
        """

        async def _do_request() -> dict[str, Any]:
            await self._ensure_session()

            session = self._session
            assert session is not None

            headers = self._get_headers()
            headers.update(kwargs.pop("headers", {}))

            async with session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid API key")  # noqa: TRY003
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError("Rate limited", retry_after=retry_after)  # noqa: TRY003
                if response.status == 404:
                    raise NotFoundError(f"Resource not found: {url}")  # noqa: TRY003

                # Retry on 5xx server errors
                if response.status >= 500:
                    raise APIError(f"Server error: {response.status}")  # noqa: TRY003

                response.raise_for_status()
                return await response.json()

        return await self._circuit_breaker.call(_do_request)

    async def list_recordings(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[HeyPocketRecording], dict[str, Any]]:
        """Fetch list of recordings with optional date and tag filtering.

        Returns:
            Tuple of (list of recordings, pagination metadata dict).
        """
        url = f"{self.config.base_url}/public/recordings"
        params: dict[str, Any] = {"page": page, "limit": limit}

        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if tags:
            params["tags"] = ",".join(tags)

        data = await self._request("GET", url, params=params)

        recordings = []
        for item in data.get("data", []):
            # List endpoint returns minimal fields - parse what we can
            recording = HeyPocketRecording.model_validate(
                {
                    "id": item.get("id", ""),
                    "title": item.get("title", "Untitled"),
                    "created_at": item.get("created_at", "1970-01-01T00:00:00Z"),
                    "updated_at": item.get("updated_at"),
                    "recording_at": item.get("recording_at"),
                    "duration": item.get("duration"),
                    "state": item.get("state", "unknown"),
                    "language": item.get("language", "en"),
                    "description": item.get("description"),
                    "tags": item.get("tags", []),
                }
            )
            recordings.append(recording)

        pagination = data.get("pagination", {})
        return recordings, pagination

    async def get_recording(
        self, recording_id: str, include_transcript: bool = True
    ) -> HeyPocketRecording:
        """Fetch full recording details including transcript and summarizations.

        Returns:
            HeyPocketRecording with full details.
        """
        url = f"{self.config.base_url}/public/recordings/{recording_id}"
        params = {"include_transcript": str(include_transcript).lower()}

        data = await self._request("GET", url, params=params)
        item = data.get("data", {})

        # Parse transcript data if present
        transcript_data = None
        if item.get("transcript"):
            transcript_data = TranscriptData.model_validate(item["transcript"])

        raw_transcript_data = None
        if item.get("raw_transcript"):
            raw_transcript_data = TranscriptData.model_validate(item["raw_transcript"])

        # Parse summarizations
        summarizations = {}
        for sid, sdata in item.get("summarizations", {}).items():
            summarizations[sid] = SummarizationData.model_validate(sdata)

        return HeyPocketRecording(
            id=item.get("id", ""),
            title=item.get("title", "Untitled"),
            created_at=datetime.fromisoformat(
                item.get("created_at", "1970-01-01T00:00:00Z").replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
            if item.get("updated_at")
            else None,
            recording_at=datetime.fromisoformat(
                item["recording_at"].replace("Z", "+00:00")
            )
            if item.get("recording_at")
            else None,
            duration=item.get("duration"),
            state=item.get("state", "unknown"),
            language=item.get("language", "en"),
            description=item.get("description"),
            transcript=transcript_data,
            raw_transcript=raw_transcript_data,
            summarizations=summarizations,
            tags=item.get("tags", []),
        )

    async def download_transcripts(
        self,
        recordings: list[HeyPocketRecording],
    ) -> tuple[list[HeyPocketRecording], list[tuple[str, Exception]]]:
        """Download transcripts for multiple recordings concurrently.

        Uses semaphore to limit concurrent downloads to max_concurrent.

        Returns:
            Tuple of (successful_recordings, failed_downloads).
            Each failed_download is (recording_id, exception).
        """
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        successes: list[HeyPocketRecording] = []
        failures: list[tuple[str, Exception]] = []

        async def download_one(rec: HeyPocketRecording) -> None:
            async with semaphore:
                try:
                    full = await self.get_recording(rec.id, include_transcript=True)
                    successes.append(full)
                except Exception as e:
                    logger.warning(
                        "Failed to download transcript for %s: %s", rec.id, e
                    )
                    failures.append((rec.id, e))

        await asyncio.gather(*[download_one(rec) for rec in recordings])

        if failures:
            logger.warning(
                "Downloaded %d/%d transcripts, %d failed",
                len(successes),
                len(recordings),
                len(failures),
            )

        return successes, failures

    async def fetch_all_since(
        self,
        since_date: str | None = None,
        tags: list[str] | None = None,
    ) -> list[HeyPocketRecording]:
        """Fetch recordings since given date with pagination and optional tag filtering.

        Returns:
            List of recordings created since the given date.
        """
        all_recordings: list[HeyPocketRecording] = []
        page = 1
        limit = 100

        while True:
            recordings, pagination = await self.list_recordings(
                start_date=since_date,
                tags=tags,
                page=page,
                limit=limit,
            )

            if not recordings:
                break

            all_recordings.extend(recordings)

            has_more = pagination.get("has_more", False)
            if isinstance(has_more, str):
                has_more = has_more.lower() == "true"
            if not has_more:
                break

            page += 1

        return all_recordings
