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

    def test_get_last_sync_date_returns_formatted_string(self, tmp_path):
        """Test get_last_sync_date returns YYYY-MM-DD string."""
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


class TestSyncStateBackup:
    """Tests for SyncState backup functionality."""

    def test_backup_to_wiki_creates_backup_file(self, tmp_path):
        """Test backup is created in wiki directory."""
        state_file = tmp_path / ".last-sync"
        backup_dir = tmp_path / "wiki"
        sync_state = SyncState(state_file, backup_dir=backup_dir)

        sync_state.set_last_sync(datetime(2026, 5, 10, 14, 30, tzinfo=UTC))

        backup_file = backup_dir / ".pocket-last-sync"
        assert backup_file.exists()
        assert "2026-05-10" in backup_file.read_text()

    def test_backup_failure_is_non_fatal(self, tmp_path):
        """Test backup failure doesn't raise exception."""
        state_file = tmp_path / ".last-sync"
        # Pass a file as backup_dir to cause failure
        backup_file = tmp_path / "backup"
        backup_file.write_text("existing")
        sync_state = SyncState(state_file, backup_dir=backup_file)

        # Should not raise
        sync_state.set_last_sync(datetime(2026, 5, 10, 14, 30, tzinfo=UTC))

    def test_backup_not_created_when_no_backup_dir(self, tmp_path):
        """Test no backup when backup_dir is None."""
        state_file = tmp_path / ".last-sync"
        sync_state = SyncState(state_file, backup_dir=None)

        sync_state.set_last_sync(datetime(2026, 5, 10, 14, 30, tzinfo=UTC))

        # No backup file should exist
        assert not (tmp_path / ".pocket-last-sync").exists()


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
