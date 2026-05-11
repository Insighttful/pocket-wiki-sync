"""CLI entry point for pocket-wiki-sync.

Provides commands for syncing HeyPocket recordings to a local wiki:
- `pocket-wiki sync`        — fetch new recordings and save to wiki
- `pocket-wiki list-synced` — list recordings already in the wiki
- `pocket-wiki show-config` — show current configuration
- `pocket-wiki clean`       — clean up sync state files and recordings

Usage:
    pocket-wiki sync [--max N] [--force] [--verbose] [--dry-run] [--tags TAGS]
    pocket-wiki list-synced
    pocket-wiki show-config
    pocket-wiki clean [--all] [--yes] [--dry-run]

Environment variables:
    HEYPOCKET_API_KEY     HeyPocket AI API key (required, starts with pk_)
    HEYPOCKET_BASE_URL    API base URL (default: https://public.heypocketai.com/api/v1)
    WIKI_PATH             Path to wiki directory (default: ~/wiki)
"""

import asyncio
from datetime import UTC
from pathlib import Path

import typer

app = typer.Typer(
    name="pocket-wiki",
    help="Sync Pocket articles to a local wiki for Obsidian.",
    add_completion=False,
)


def _run_async(coro):
    """Run an async coroutine, handling both nested and top-level event loops.

    Returns:
        Result of the coroutine execution.
    """
    try:
        loop = asyncio.get_running_loop()
        # We're already in a running event loop (e.g., from typer or another
        # async context)
        # Use create_task to run the coroutine without blocking
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        return asyncio.run(coro)


def _parse_tag_filter(tags: str | None) -> list[str] | None:
    """Parse comma-separated tag filter string into a list.

    Returns:
        List of tag strings, or None if tags is empty.
    """
    if not tags:
        return None
    parsed = [t.strip() for t in tags.split(",") if t.strip()]
    if parsed:
        typer.echo(f"Filtering by tags: {parsed}")
    return parsed or None


def _display_recordings(recordings: list, verbose: bool) -> None:
    """Display fetched recordings in verbose mode."""
    if not verbose:
        return
    for r in recordings:
        tag_names = []
        for tag in (r.tags or [])[:3]:
            if isinstance(tag, str):
                tag_names.append(tag)
            elif isinstance(tag, dict):
                tag_names.append(tag.get("name", tag.get("label", str(tag))))
        tags_str = f" [{', '.join(tag_names)}]" if tag_names else ""
        typer.echo(f"  - {r.created_at.strftime('%Y-%m-%d')} {r.title[:50]}{tags_str}")


def _handle_sync_error(e: Exception) -> None:
    """Handle sync errors by printing diagnostic message and exiting.

    Raises:
        typer.Exit: Always raised after handling the error.
    """
    if isinstance(e, PermissionError):
        typer.echo(f"\n✗ Authentication failed: {e}", err=True)
    elif isinstance(e, RuntimeError):
        error_msg = str(e)
        if "502" in error_msg or "temporarily unavailable" in error_msg.lower():
            typer.echo(
                "\n✗ HeyPocket API is temporarily unavailable. Please try again later.",
                err=True,
            )
        elif "rate limit" in error_msg.lower():
            typer.echo(
                "\n✗ Rate limited by HeyPocket API. Please wait before trying again.",
                err=True,
            )
        else:
            typer.echo(f"\n✗ Sync failed: {e}", err=True)
    else:
        typer.echo(f"\n✗ Unexpected error: {type(e).__name__}: {e}", err=True)
        import traceback

        typer.echo(traceback.format_exc(), err=True)
    raise typer.Exit(code=1) from None


async def _run_sync_impl(
    client,
    wiki_output,
    wiki_env,
    force: bool,
    max_items: int,
    tags: str | None,
    lock,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Execute the sync operation."""
    import time
    from datetime import datetime

    from shared.sync_state import SyncState

    state_file = Path(__file__).parent.parent / ".last-sync"
    sync_state = SyncState(state_file, backup_dir=wiki_env.wiki_path)

    last_sync_date = None if force else sync_state.get_last_sync_date()
    tag_list = _parse_tag_filter(tags)

    if last_sync_date:
        typer.echo(f"Fetching recordings since {last_sync_date}...")
    else:
        typer.echo(f"Fetching up to {max_items} recordings (full sync)...")

    start_time = time.time()

    try:
        recordings = await client.fetch_all_since(
            since_date=last_sync_date, tags=tag_list
        )

        if max_items and len(recordings) > max_items:
            recordings = recordings[:max_items]

        elapsed = time.time() - start_time
        typer.echo(f"Fetched {len(recordings)} recording(s) in {elapsed:.1f}s")

        _display_recordings(recordings, verbose)

        if not recordings:
            typer.echo("No new recordings found.")
            return

        if dry_run:
            typer.echo(f"\n[Dry Run] Would sync {len(recordings)} recording(s):")
            for r in recordings:
                typer.echo(f"  - {r.title[:60]}")
            typer.echo("\nNo files written (dry-run mode)")
            return

        typer.echo(f"Downloading {len(recordings)} transcript(s)...")

        (
            recordings_with_transcripts,
            failed_downloads,
        ) = await client.download_transcripts(recordings)
        if failed_downloads:
            typer.echo(
                f"  Warning: {len(failed_downloads)} transcript(s) failed to download"
            )

        typer.echo(
            f"Saving {len(recordings_with_transcripts)} transcript(s) to wiki..."
        )

        saved = []
        for recording in recordings_with_transcripts:
            result = wiki_output.save_recording(recording)
            if result:
                saved.append(recording)
                typer.echo(f"  ✓ {recording.title}")
            else:
                typer.echo(f"  - Skipped (already exists): {recording.title}")

        if saved:
            wiki_output.update_sources_index(saved)
            wiki_output.create_sync_log(saved)

        if recordings:
            latest_timestamp = max(r.created_at for r in recordings)
            sync_state.set_last_sync(latest_timestamp)
        elif saved:
            sync_state.set_last_sync(datetime.now(UTC))

        typer.echo(f"\n✓ Synced {len(saved)} recording(s) to {wiki_env.wiki_path}")

    except Exception as e:
        _handle_sync_error(e)
    finally:
        await client.close()
        lock.release()


@app.command()
def sync(
    max_items: int = typer.Option(
        100, "--max", "-m", help="Maximum recordings to fetch"
    ),
    wiki_path: str | None = typer.Option(
        None, "--wiki", "-w", help="Path to wiki directory"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force full sync (ignore last sync timestamp)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Preview what would be synced without writing files",
    ),
    tags: str | None = typer.Option(
        None,
        "--tags",
        "-t",
        help="Filter by tags (comma-separated, e.g., 'work,meeting')",
    ),
):
    """Fetch new HeyPocket recordings and save them to a local wiki.

    Raises:
        typer.Exit: If credentials are missing, another sync is running,
            or the sync operation fails.
    """
    from modules.wiki import WikiOutput
    from shared.environment import get_wiki_env
    from shared.pocket.client import HeyPocketClient
    from shared.pocket.config import HeyPocketConfig
    from shared.sync_state import SyncLock

    if wiki_path:
        import os

        os.environ["WIKI_PATH"] = wiki_path

    try:
        config = HeyPocketConfig.from_environment()
    except ValueError as e:
        typer.echo(f"Error loading HeyPocket credentials: {e}", err=True)
        raise typer.Exit(code=1) from None

    # Fail-fast: validate API key is present before attempting any API call
    if not config.api_key:
        typer.echo(
            "Error: HEYPOCKET_API_KEY is not set. "
            "Set it in your .env file or export it as an environment variable.",
            err=True,
        )
        raise typer.Exit(code=1) from None

    wiki_env = get_wiki_env()
    wiki_output = WikiOutput(wiki_env)
    wiki_output.ensure_directories()

    lock = SyncLock(Path(__file__).parent.parent)
    if not lock.acquire():
        typer.echo(
            "Error: Another sync is already running. Use --force to override.", err=True
        )
        raise typer.Exit(code=1)

    client = HeyPocketClient(config)

    try:
        _run_async(
            _run_sync_impl(
                client,
                wiki_output,
                wiki_env,
                force,
                max_items,
                tags,
                lock,
                verbose,
                dry_run,
            )
        )
    except KeyboardInterrupt:
        lock.release()
        typer.echo("\nSync interrupted.")
        raise typer.Exit(code=130) from None


@app.command()
def list_synced(
    wiki_path: str | None = typer.Option(
        None, "--wiki", "-w", help="Path to wiki directory"
    ),
):
    """List recordings already synced to the wiki (local files only)."""
    import os

    from shared.environment import get_wiki_env

    if wiki_path:
        os.environ["WIKI_PATH"] = wiki_path

    env = get_wiki_env()
    pocket_dir = env.wiki_path / "raw" / "pocket"

    if not pocket_dir.exists():
        typer.echo("No recordings synced yet. Run 'pocket-wiki sync' first.")
        return

    articles = sorted(pocket_dir.glob("*.md"))
    if not articles:
        typer.echo("No recordings found in wiki directory.")
        return

    typer.echo(f"Synced recordings ({len(articles)} total):\n")
    for article in articles:
        # Extract title from filename
        title = article.stem.replace("-", " ").title()
        typer.echo(f"  {article.name}")
        typer.echo(f"    → {title}")


@app.command()
def show_config():
    """Show current configuration."""
    import os

    # Show environment variables
    typer.echo("Configuration:")
    typer.echo("-------------")
    api_key_status = "[set]" if os.environ.get("HEYPOCKET_API_KEY") else "[not set]"
    typer.echo(f"  HEYPOCKET_API_KEY:    {api_key_status}")
    typer.echo(
        f"  HEYPOCKET_BASE_URL:   {os.environ.get('HEYPOCKET_BASE_URL', 'https://public.heypocketai.com/api/v1')}"
    )
    typer.echo(f"  WIKI_PATH:           {os.environ.get('WIKI_PATH', '~/wiki')}")
    typer.echo()

    # Show config validity
    if not os.environ.get("HEYPOCKET_API_KEY"):
        typer.echo("⚠  HEYPOCKET_API_KEY is not set.", err=True)
        typer.echo(
            "   Set it in your .env file or export it as an environment variable.",
            err=True,
        )
        typer.echo(
            "   Commands that call the API (sync) will fail without it.",
            err=True,
        )
    else:
        key = os.environ["HEYPOCKET_API_KEY"]
        prefix = key[:6] if len(key) > 10 else key
        typer.echo(f"   API key starts with: {prefix}...")
        typer.echo("   ✓ API key is configured.")

    typer.echo()


@app.command()
def clean(
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Also delete all synced recordings from raw/pocket/",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Preview what would be cleaned without deleting anything",
    ),
):
    """Clean up sync state files and optionally delete synced recordings.

    Removes .last-sync, .sync-lock, and (if --all is passed) all recordings
    in the wiki's raw/pocket/ directory.

    Raises:
        typer.Exit: If user cancels the confirmation prompt.
    """
    from pathlib import Path

    from shared.environment import get_wiki_env

    project_root = Path(__file__).parent
    wiki_env = get_wiki_env()

    paths, labels = _gather_clean_targets(project_root, wiki_env, all)

    if not labels:
        typer.echo("Nothing to clean — no state files or recordings found.")
        return

    typer.echo("The following will be removed:\n")
    for label in labels:
        typer.echo(f"  • {label}")

    if dry_run:
        typer.echo("\n[Dry Run] No files were deleted.")
        return

    if not yes:
        typer.echo()
        confirm = typer.confirm("Proceed with cleanup?")
        if not confirm:
            typer.echo("Cleanup cancelled.")
            raise typer.Exit(code=0)

    removed_count = _execute_cleanup(paths)
    typer.echo(f"\n✓ Cleaned {removed_count} item(s).")


def _gather_clean_targets(
    project_root: Path, wiki_env, include_recordings: bool
) -> tuple[list[Path], list[str]]:
    """Gather paths to clean and their display labels.

    Returns:
        Tuple of (list of paths to remove, list of display strings).
    """
    paths: list[Path] = []
    labels: list[str] = []

    # Check project root state files
    state_file = project_root / ".last-sync"
    lock_file = project_root / ".sync-lock"

    if state_file.exists():
        paths.append(state_file)
        labels.append(f"{state_file}  (sync state)")
    if lock_file.exists():
        paths.append(lock_file)
        labels.append(f"{lock_file}  (sync lock)")

    # Check wiki backups
    backup_file = wiki_env.wiki_path / ".pocket-last-sync"
    if backup_file.exists():
        paths.append(backup_file)
        labels.append(f"{backup_file}  (wiki backup)")

    # Check raw/pocket recordings
    if include_recordings:
        pocket_dir = wiki_env.wiki_path / "raw" / "pocket"
        if pocket_dir.exists():
            md_files = list(pocket_dir.glob("*.md"))
            if md_files:
                paths.extend(md_files)
                labels.append(f"{pocket_dir}  ({len(md_files)} recording(s))")

    return paths, labels


def _execute_cleanup(targets: list[Path]) -> int:
    """Remove all target paths and return the count of removed items.

    Returns:
        Number of items successfully removed.
    """
    import contextlib

    removed = 0
    for path in targets:
        with contextlib.suppress(OSError):
            path.unlink()
            removed += 1

    # Try to clean up empty pocket dir after removing recordings
    for path in targets:
        if path.parent.name == "pocket" and path.suffix == ".md":
            with contextlib.suppress(OSError):
                path.parent.rmdir()
            break  # only need to try once

    return removed


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
