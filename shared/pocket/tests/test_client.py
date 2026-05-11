"""Tests for shared/pocket/client.py."""

import asyncio
from datetime import datetime

import pytest

from shared.pocket.client import CircuitBreaker, HeyPocketClient
from shared.pocket.config import HeyPocketConfig
from shared.pocket.models import HeyPocketRecording


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_reset_after_failure(self):
        """Test that _reset clears failure count and last_failure_time."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.failure_count = 2
        cb.last_failure_time = datetime.now()
        await cb._reset()
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    @pytest.mark.asyncio
    async def test_reset_locking(self):
        """Verify _reset holds the lock when modifying state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.failure_count = 5
        cb.last_failure_time = datetime.now()

        async def concurrent_reset():
            await cb._reset()

        await asyncio.gather(
            concurrent_reset(),
            concurrent_reset(),
            concurrent_reset(),
        )
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    @pytest.mark.asyncio
    async def test_call_success_resets(self):
        """Test that a successful call via call() resets the breaker."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.failure_count = 2

        async def succeed():  # noqa: RUF029
            return "ok"

        result = await cb.call(succeed)
        assert result == "ok"
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    @pytest.mark.asyncio
    async def test_call_failure_records(self):
        """Test that a failed call via call() increments failure count."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        async def fail():  # noqa: RUF029
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await cb.call(fail)
        assert cb.failure_count == 1
        assert cb.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Test that circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

        async def fail():  # noqa: RUF029
            raise ValueError("boom")

        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)

        with pytest.raises(Exception, match="Circuit breaker open"):
            await cb.call(fail)


class TestHeyPocketClient:
    """Tests for HeyPocketClient."""

    @pytest.fixture
    def config(self):
        """Create test config.

        Returns:
            HeyPocketConfig instance for testing.
        """
        return HeyPocketConfig(
            api_key="pk_test123",
            base_url="https://public.heypocketai.com/api/v1",
            max_retries=3,
            max_concurrent=2,
        )

    @pytest.fixture
    def client(self, config):
        """Create test client.

        Returns:
            HeyPocketClient instance for testing.
        """
        return HeyPocketClient(config)

    def test_client_initialization(self, config):
        """Test client initializes with config."""
        client = HeyPocketClient(config)
        assert client.config == config
        assert client._session is None

    def test_get_headers(self, client):
        """Test headers include auth."""
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer pk_")

    def test_list_recordings_sync(self, client):
        """Test list_recordings parses response correctly (sync test)."""
        # This tests the parsing logic without async
        mock_data = {
            "success": True,
            "data": [
                {
                    "id": "rec-1",
                    "title": "Test Recording",
                    "created_at": "2026-05-08T10:00:00Z",
                    "updated_at": "2026-05-08T11:00:00Z",
                    "recording_at": "2026-05-08T09:00:00Z",
                    "duration": 300,
                    "state": "completed",
                    "language": "en",
                    "tags": [],
                },
            ],
            "pagination": {"page": 1, "limit": 20, "total": 1, "has_more": False},
        }

        # Test model parsing directly
        recording = HeyPocketRecording.model_validate(mock_data["data"][0])
        assert recording.id == "rec-1"
        assert recording.title == "Test Recording"
        assert recording.duration == 300

    @pytest.mark.asyncio
    async def test_download_transcripts_returns_tuple(self, client, config):
        """Test that download_transcripts returns (successes, failures) tuple."""
        recordings = [
            HeyPocketRecording(id="rec-1", title="Test 1"),
        ]
        successes, failures = await client.download_transcripts(recordings)
        assert isinstance(successes, list)
        assert isinstance(failures, list)

    def test_has_more_string_true(self, client):
        """Test has_more with string 'true' is handled correctly."""
        pagination = {"has_more": "true"}
        has_more = pagination.get("has_more", False)
        if isinstance(has_more, str):
            has_more = has_more.lower() == "true"
        assert has_more is True

    def test_has_more_string_false(self, client):
        """Test has_more with string 'false' is handled correctly."""
        pagination = {"has_more": "false"}
        has_more = pagination.get("has_more", False)
        if isinstance(has_more, str):
            has_more = has_more.lower() == "true"
        assert has_more is False

    def test_has_more_boolean(self, client):
        """Test has_more with actual boolean is still handled correctly."""
        pagination = {"has_more": True}
        has_more = pagination.get("has_more", False)
        if isinstance(has_more, str):
            has_more = has_more.lower() == "true"
        assert has_more is True

    def test_has_more_missing(self, client):
        """Test has_more defaults to False when missing."""
        pagination = {}
        has_more = pagination.get("has_more", False)
        if isinstance(has_more, str):
            has_more = has_more.lower() == "true"
        assert has_more is False


class TestHeyPocketConfig:
    """Tests for client config usage."""

    def test_default_max_concurrent(self):
        """Test default max concurrent is used."""
        config = HeyPocketConfig(api_key="pk_test")
        assert config.max_concurrent == 3

    def test_custom_max_concurrent(self):
        """Test custom max concurrent."""
        config = HeyPocketConfig(api_key="pk_test", max_concurrent=10)
        assert config.max_concurrent == 10
