"""Environment configuration using pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(BaseSettings):
    """Base environment configuration for pocket-wiki-sync."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class WikiEnvironment(Environment):
    """Wiki-specific environment configuration."""

    wiki_path: Path = Field(
        default=Path.home() / "wiki",
        description="Path to wiki directory",
    )


class PocketEnvironment(Environment):
    """Pocket API environment configuration."""

    pocket_consumer_key: str = Field(default="", alias="POCKET_CONSUMER_KEY")
    pocket_access_token: str = Field(default="", alias="POCKET_ACCESS_TOKEN")
    pocket_max_retries: int = Field(default=3, alias="POCKET_MAX_RETRIES")
    pocket_base_delay: float = Field(default=1.0, alias="POCKET_BASE_DELAY")
    pocket_max_delay: float = Field(default=60.0, alias="POCKET_MAX_DELAY")
    pocket_rate_limit_per_minute: int = Field(
        default=60, alias="POCKET_RATE_LIMIT_PER_MINUTE"
    )


class HeyPocketEnvironment(Environment):
    """HeyPocket AI API environment configuration."""

    heypocket_api_key: str = Field(default="", alias="HEYPOCKET_API_KEY")
    heypocket_base_url: str = Field(
        default="https://public.heypocketai.com/api/v1",
        alias="HEYPOCKET_BASE_URL",
    )
    heypocket_max_retries: int = Field(default=3, alias="HEYPOCKET_MAX_RETRIES")
    heypocket_max_concurrent: int = Field(default=3, alias="HEYPOCKET_MAX_CONCURRENT")


class ScraperEnvironment(Environment):
    """Scraper environment configuration."""

    # Rate limiting
    min_delay_seconds: float = Field(default=1.0)
    max_delay_seconds: float = Field(default=3.0)
    jitter_factor: float = Field(default=0.5)

    # Discovery settings
    max_discovery_depth: int = Field(default=5)
    max_pages_to_discover: int = Field(default=100)
    follow_external_links: bool = Field(default=False)

    # Site configuration
    site_name: str = Field(default="heypocket")
    base_url: str = Field(default="https://docs.heypocketai.com")

    # Playwright settings
    headless: bool = Field(default=True)
    timeout_ms: int = Field(default=30000)
    wait_until: str = Field(default="networkidle")


def get_wiki_env() -> WikiEnvironment:
    """Get wiki environment configuration.

    Returns:
        WikiEnvironment instance.
    """
    return WikiEnvironment()


def get_pocket_env() -> PocketEnvironment:
    """Get Pocket environment configuration.

    Returns:
        PocketEnvironment instance.
    """
    return PocketEnvironment()


def get_heypocket_env() -> HeyPocketEnvironment:
    """Get HeyPocket environment configuration.

    Returns:
        HeyPocketEnvironment instance.
    """
    return HeyPocketEnvironment()


def get_scraper_env() -> ScraperEnvironment:
    """Get scraper environment configuration.

    Returns:
        ScraperEnvironment instance.
    """
    return ScraperEnvironment()
