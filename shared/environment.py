"""Environment configuration using pydantic-settings.

.env is the source of truth: on import we load it with override=True so its
values take precedence over any in-memory environment variables. This ensures
changes to .env or deletion of state files are always respected, and avoids
in-memory env pollution across runs/commands.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure .env is authoritative for this process (idempotent).
load_dotenv(".env", override=True)


class Environment(BaseSettings):
    """Base environment configuration for pocket-wiki-sync."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class WikiEnvironment(Environment):
    """Wiki-specific environment configuration.

    Uses WIKI_RAW_PATH to align with Karpathy's LLM Wiki convention:
    raw files are stored under a 'raw' directory in the wiki root.
    """

    wiki_raw_path: Path = Field(
        default=Path.home() / "wiki",
        alias="WIKI_RAW_PATH",
        description="Root path to the wiki where raw/pocket/ will be created.",
    )


def _ensure_wiki_raw_path_in_env() -> None:
    """Ensure WIKI_RAW_PATH is set in .env (source of truth).

    If missing or empty in .env, prompts the user once and persists it.
    We intentionally do NOT mutate os.environ here; pydantic-settings reads
    directly from .env with env_file_priority=True.
    """
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"

    # Check if WIKI_RAW_PATH is already defined in .env
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("WIKI_RAW_PATH"):
                value = stripped.split("=", 1)[1].strip().strip("\"'")
                if value:
                    return

    # Not set yet -> prompt user
    import typer

    default_value = str(Path.home() / "wiki/raw")
    typer.echo("Transcripts will be saved directly into the path you provide.")
    prompt = f"Enter transcripts directory (default {default_value}): "
    user_input = input(prompt).strip()
    chosen = user_input or default_value

    # Read existing .env content
    env_content = ""
    if env_path.exists():
        env_content = env_path.read_text(encoding="utf-8")

    lines = []
    updated = False
    for line in env_content.splitlines(keepends=True) or []:
        if line.strip().startswith("WIKI_RAW_PATH"):
            lines.append(f"WIKI_RAW_PATH={chosen}\n")
            updated = True
        else:
            lines.append(line)

    # Append if not already present
    if not updated:
        if env_content and not env_content.endswith("\n"):
            lines.append("\n")
        lines.append(f"WIKI_RAW_PATH={chosen}\n")

    with Path(env_path).open("w", encoding="utf-8") as f:
        f.writelines(lines)


def get_wiki_env() -> WikiEnvironment:
    """Get wiki environment configuration.

    On first run, if WIKI_RAW_PATH is not set, prompts the user once and
    persists it to .env (no restart required).

    Returns:
        WikiEnvironment instance.
    """
    _ensure_wiki_raw_path_in_env()
    return WikiEnvironment()


class HeyPocketEnvironment(Environment):
    """HeyPocket AI API environment configuration."""

    heypocket_api_key: str = Field(default="", alias="HEYPOCKET_API_KEY")
    heypocket_base_url: str = Field(
        default="https://public.heypocketai.com/api/v1",
        alias="HEYPOCKET_BASE_URL",
    )
    heypocket_max_retries: int = Field(default=3, alias="HEYPOCKET_MAX_RETRIES")
    heypocket_max_concurrent: int = Field(default=3, alias="HEYPOCKET_MAX_CONCURRENT")


class SyncEnvironment(Environment):
    """Sync behavior configuration."""

    ignore_private_tags: bool = Field(
        default=True,
        description="Ignore recordings tagged as personal or private",
    )


def get_sync_env() -> SyncEnvironment:
    """Get sync environment configuration.

    Returns:
        SyncEnvironment instance.
    """
    return SyncEnvironment()


def get_heypocket_env() -> HeyPocketEnvironment:
    """Get HeyPocket environment configuration.

    Returns:
        HeyPocketEnvironment instance.
    """
    return HeyPocketEnvironment()
