"""Tests for sync state management."""

from datetime import UTC, datetime

from shared.sync_state import SyncLock, SyncState


class TestSyncState:
    """Tests for SyncState class."""

    def test_get_last_sync_returns_none_when_no_file(self, tmp_path):
        """Test get_last_sync returns None when state file doesn't exist."""
        state_file = tmp_path / ".last-sync"
        sync_state = SyncState(state_file)

        result = sync_state.get_last_sync()

        assert result is None

    def test_get_last_sync_returns_datetime_when_file_exists(self, tmp_path):
        """Test get_last_sync returns datetime when state file exists."""
        state_file = tmp_path / ".last-sync"
        state_file.write_text("2026-05-10T14:30:00+00:00")
        sync_state = SyncState(state_file)

        result = sync_state.get_last_sync()

        assert result is not None
        assert result.year == 2026
        assert result.month == 5
        assert result.day == 10

    def test_set_last_sync_creates_file(self, tmp_path):
        """Test set_last_sync creates the state file."""
        state_file = tmp_path / ".last-sync"
        sync_state = SyncState(state_file)

        sync_state.set_last_sync(datetime(2026, 5, 10, 14, 30, tzinfo=UTC))

        assert state_file.exists()
        assert "2026-05-10" in state_file.read_text()

    def test_get_last_sync_iso_returns_iso_string(self, tmp_path):
        """Test get_last_sync_iso returns full ISO timestamp."""
        state_file = tmp_path / ".last-sync"
        state_file.write_text("2026-05-10T14:30:00+00:00")
        sync_state = SyncState(state_file)

        result = sync_state.get_last_sync_iso()

        assert result is not None
        assert "2026-05-10T14:30:00" in result

    def test_get_last_sync_iso_returns_none_when_no_file(self, tmp_path):
        """Test get_last_sync_iso returns None when no file."""
        state_file = tmp_path / ".last-sync"
        sync_state = SyncState(state_file)

        result = sync_state.get_last_sync_iso()

        assert result is None

    def test_get_last_sync_date_returns_yyyy_mm_dd(self, tmp_path):
        """Test get_last_sync_date returns YYYY-MM-DD for API calls."""
        state_file = tmp_path / ".last-sync"
        state_file.write_text("2026-05-10T14:30:00+00:00")
        sync_state = SyncState(state_file)

        result = sync_state.get_last_sync_date()

        assert result == "2026-05-10"

    def test_get_last_sync_date_returns_none_when_no_file(self, tmp_path):
        """Test get_last_sync_date returns None when no file."""
        state_file = tmp_path / ".last-sync"
        sync_state = SyncState(state_file)

        result = sync_state.get_last_sync_date()

        assert result is None


class TestSyncLock:
    """Tests for SyncLock class."""

    def test_acquire_creates_lock_file(self, tmp_path):
        """Test acquire creates lock file."""
        lock = SyncLock(tmp_path)

        result = lock.acquire()

        assert result is True
        assert (tmp_path / ".sync-lock").exists()

    def test_acquire_fails_when_lock_exists(self, tmp_path):
        """Test acquire returns False when lock file exists."""
        lock_path = tmp_path / ".sync-lock"
        lock_path.write_text(datetime.now(UTC).isoformat())
        lock = SyncLock(tmp_path)

        result = lock.acquire()

        assert result is False

    def test_acquire_succeeds_when_lock_is_stale(self, tmp_path):
        """Test acquire succeeds when lock is older than 1 hour."""
        lock_path = tmp_path / ".sync-lock"
        # Create stale lock (2 hours old)
        stale_time = datetime.now(UTC).timestamp() - 7200
        lock_path.write_text(datetime.fromtimestamp(stale_time, tz=UTC).isoformat())
        lock = SyncLock(tmp_path)

        result = lock.acquire()

        assert result is True

    def test_release_removes_lock_file(self, tmp_path):
        """Test release removes lock file."""
        lock = SyncLock(tmp_path)
        lock.acquire()

        lock.release()

        assert not (tmp_path / ".sync-lock").exists()

    def test_release_is_safe_when_no_lock(self, tmp_path):
        """Test release doesn't fail when no lock exists."""
        lock = SyncLock(tmp_path)

        # Should not raise
        lock.release()
