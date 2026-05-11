"""Sync state management for tracking last sync timestamp."""

from datetime import UTC, datetime
from pathlib import Path


class SyncState:
    """Manages the last sync timestamp for incremental syncs."""

    def __init__(self, state_file: Path, backup_dir: Path | None = None):
        self.state_file = state_file
        self.backup_dir = backup_dir

    def get_last_sync(self) -> datetime | None:
        """Read the last sync timestamp from state file.

        Returns:
            Datetime of last sync, or None if never synced.
        """
        if not self.state_file.exists():
            return None

        try:
            timestamp = self.state_file.read_text().strip()
            if timestamp:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except (ValueError, OSError):
            pass
        return None

    def set_last_sync(self, timestamp: datetime | None = None) -> None:
        """Write the last sync timestamp to state file and optionally backup."""
        if timestamp is None:
            timestamp = datetime.now(UTC)

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(timestamp.isoformat())

        # Backup to wiki directory if configured
        if self.backup_dir:
            self._backup_to_wiki(timestamp)

    def _backup_to_wiki(self, timestamp: datetime) -> None:
        """Backup last sync to wiki directory."""
        if not self.backup_dir:
            return
        try:
            backup_path = self.backup_dir / ".pocket-last-sync"
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(timestamp.isoformat())
        except OSError:
            pass  # Backup failure is non-fatal

    def get_last_sync_date(self) -> str | None:
        """Get last sync date as YYYY-MM-DD string for API.

        Returns:
            Date string in YYYY-MM-DD format, or None if never synced.
        """
        last_sync = self.get_last_sync()
        if last_sync:
            return last_sync.strftime("%Y-%m-%d")
        return None


class SyncLock:
    """Manages sync lock file to prevent concurrent syncs."""

    LOCK_FILE = ".sync-lock"

    def __init__(self, lock_dir: Path):
        self.lock_dir = lock_dir
        self.lock_path = lock_dir / self.LOCK_FILE

    def acquire(self) -> bool:
        """Try to acquire lock.

        Returns:
            True if lock was acquired, False if already locked.
        """
        if self.lock_path.exists():
            # Check if lock is stale (older than 1 hour)
            try:
                lock_time = datetime.fromisoformat(
                    self.lock_path.read_text().replace("Z", "+00:00")
                )
                age = datetime.now(UTC) - lock_time
                if age.total_seconds() > 3600:
                    # Lock is stale, remove it
                    self.lock_path.unlink()
                    return self._create_lock()
            except (ValueError, OSError):
                # Lock file corrupted, remove it
                self.lock_path.unlink()
                return self._create_lock()
            else:
                return False
        return self._create_lock()

    def _create_lock(self) -> bool:
        """Create the lock file.

        Returns:
            True if lock was created, False otherwise.
        """
        try:
            self.lock_dir.mkdir(parents=True, exist_ok=True)
            self.lock_path.write_text(datetime.now(UTC).isoformat())
        except OSError:
            return False
        else:
            return True

    def release(self) -> None:
        """Release the lock."""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except OSError:
            pass
